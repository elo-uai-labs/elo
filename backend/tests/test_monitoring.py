import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from domain import Store, initial_state, transition as domain_transition, WorkflowError
import monitoring


class MemoryStore:
    def __init__(self):
        self.state = initial_state()
        domain_transition(self.state, 'detect', {})
        self.writes = 0
        self.principals = []

    def read(self):
        return {**copy.deepcopy(self.state), 'audit_valid': True}

    def apply(self, command, data, authorize=None):
        assert command == 'integration/import'
        self.principals.append(authorize(self.state))
        monitoring.transition(self.state, data)
        self.writes += 1
        return self.read()


class MonitoringTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.store = MemoryStore()
        self.wrapper = {'synthetic': True, 'dataset': {
            'employees': [{'id': 'EMP-MON', 'name': 'Pessoa fictícia', 'role': 'Aprovador', 'contact_code': 'SYN-MON'}],
            'suppliers': [{'id': 'FOR-MON', 'name': 'Fornecedor fictício', 'contact_code': 'SYN-MON'}],
            'contracts': [{'id': 'CTR-MON', 'title': 'Contrato fictício', 'supplier_id': 'FOR-MON', 'approver_id': 'EMP-MON'}],
        }}
        self.data = {'source_id': 'demo-source', 'source_name': 'batch.json', 'payload': self.wrapper}

    def test_batch_import_detect_and_transactional_duplicate_guard(self):
        action, actor, details = monitoring.transition(self.store.state, self.data)
        self.assertEqual(action, 'Integração sintética executada')
        self.assertEqual(actor, 'Conector sintético:demo-source')
        self.assertEqual(details['case_ids'], ['ELO-MON'])
        self.assertEqual(set(details['contracts_analyzed']), {'CTR-MON', 'CTR-1042', 'CTR-1091'})
        self.assertEqual([rule['id'] for rule in details['rules']], ['contact-code-match', 'supplier-shared-contact'])
        before = copy.deepcopy(self.store.state)
        with self.assertRaises(WorkflowError):
            monitoring.transition(self.store.state, self.data)
        self.assertEqual(self.store.state, before)
        renamed = {**self.data, 'source_name': 'renamed.json'}
        self.assertEqual(monitoring.batch_identity(renamed)[2], details['content_sha256'])

    def test_failed_import_rolls_back_everything_and_can_retry(self):
        self.wrapper['dataset']['contracts'][0]['approver_id'] = 'EMP-MISSING'
        before = copy.deepcopy(self.store.state)
        with self.assertRaises(WorkflowError):
            monitoring.transition(self.store.state, self.data)
        self.assertEqual(self.store.state, before)
        self.wrapper['dataset']['contracts'][0]['approver_id'] = 'EMP-MON'
        monitoring.transition(self.store.state, self.data)
        self.assertEqual(len(self.store.state['integration_batches']), 1)

    def test_employee_only_batch_has_zero_detected_or_scanned(self):
        self.wrapper['dataset']['contracts'] = []
        self.wrapper['dataset']['suppliers'] = []
        _, _, details = monitoring.transition(self.store.state, self.data)
        self.assertEqual(details['case_ids'], [])
        self.assertEqual(details['contracts_analyzed'], [])

    def test_new_supplier_reanalyzes_old_contract_for_secondary_rule(self):
        domain_transition(self.store.state, 'detect', {'rule_id': 'supplier-shared-contact'})
        self.wrapper['dataset'] = {'employees': [], 'contracts': [], 'suppliers': [
            {'id': 'FOR-NEW-PEER', 'name': 'Fornecedor fictício novo', 'contact_code': 'FICT-801'}]}
        _, _, details = monitoring.transition(self.store.state, self.data)
        self.assertEqual(details['case_ids'], ['SIG-SUP-CTR-1042'])
        self.assertEqual([rule['id'] for rule in details['rules']], ['supplier-shared-contact'])
        self.assertEqual(set(details['contracts_analyzed']), {'CTR-1042', 'CTR-1091'})

    def test_once_is_idempotent_and_logs_no_dataset_or_content(self):
        (self.directory / 'batch.json').write_text(json.dumps(self.wrapper))
        output = []
        self.assertEqual(monitoring.run_once(self.store, self.directory, 'demo', output.append), {'processed': 1, 'duplicate': 0, 'failed': 0})
        self.assertEqual(monitoring.run_once(self.store, self.directory, 'demo', output.append), {'processed': 0, 'duplicate': 1, 'failed': 0})
        self.assertEqual(self.store.writes, 1)
        self.assertEqual(self.store.principals, [{'mode': 'local-service', 'service_id': 'demo'}])
        self.assertNotIn('SYN-MON', ''.join(output))
        self.assertNotIn('Fornecedor fictício', ''.join(output))

    def test_file_path_regular_type_size_and_wrapper_limits(self):
        target = self.directory / 'batch.json'
        target.write_text(json.dumps(self.wrapper))
        link = self.directory / 'link.json'
        link.symlink_to(target)
        with self.assertRaises(WorkflowError):
            monitoring.read_batch(link, 'demo')
        directory = self.directory / 'directory.json'
        directory.mkdir()
        with self.assertRaises(WorkflowError):
            monitoring.read_batch(directory, 'demo')
        if hasattr(os, 'mkfifo'):
            fifo = self.directory / 'pipe.json'
            os.mkfifo(fifo)
            with self.assertRaises(WorkflowError):
                monitoring.read_batch(fifo, 'demo')
        target.write_bytes(b' ' * (monitoring.MAX_FILE_BYTES + 1))
        with self.assertRaises(WorkflowError):
            monitoring.read_batch(target, 'demo')
        for changed in ({'source_id': '../escape'}, {'source_name': '../batch.json'}, {'source_name': 'bad\n.json'}, {'payload': {'synthetic': False, 'dataset': {}}}):
            with self.assertRaises(WorkflowError):
                monitoring.batch_identity({**self.data, **changed})

    def test_loop_backoff_is_bounded_and_interruptible(self):
        (self.directory / 'bad.json').write_text('{invalid')
        delays = []
        def stop(delay):
            delays.append(delay)
            if len(delays) == 3:
                raise KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            monitoring.run_loop(self.store, self.directory, 'demo', 10, emit=lambda line: None, sleep=stop)
        self.assertEqual(delays, [20, 40, 80])
        self.assertEqual(self.store.writes, 0)

    def test_open_directory_anchor_survives_inbox_path_replacement(self):
        inbox = self.directory / 'inbox'
        inbox.mkdir()
        (inbox / 'batch.json').write_text(json.dumps(self.wrapper))
        outside = self.directory / 'outside'
        outside.mkdir()
        (outside / 'batch.json').write_text('{malicious-invalid')
        original_read = monitoring.read_batch
        def replace_then_read(path, source_id, directory_fd=None):
            inbox.rename(self.directory / 'original-inbox')
            inbox.symlink_to(outside, target_is_directory=True)
            return original_read(path, source_id, directory_fd=directory_fd)
        with patch('monitoring.read_batch', side_effect=replace_then_read):
            result = monitoring.run_once(self.store, inbox, 'demo', emit=lambda line: None)
        self.assertEqual(result, {'processed': 1, 'duplicate': 0, 'failed': 0})
        self.assertEqual(self.store.writes, 1)

    def test_cli_requires_explicit_database_and_runs_once_only_on_temp_path(self):
        with self.assertRaises(SystemExit):
            monitoring.main(['--inbox', str(self.directory), '--source-id', 'demo', '--once'])
        db = self.directory / 'explicit.sqlite3'
        with patch('monitoring.Store', return_value=self.store) as constructor, patch('builtins.print'):
            result = monitoring.main(['--inbox', str(self.directory), '--db', str(db), '--source-id', 'demo', '--once'])
        constructor.assert_called_once_with(db)
        self.assertEqual(result, 0)

    def test_real_cli_once_restarts_with_idempotent_temporary_database(self):
        inbox = self.directory / 'actual-inbox'
        inbox.mkdir()
        (inbox / 'batch.json').write_text(json.dumps(self.wrapper))
        db = self.directory / 'actual.sqlite3'
        command = [sys.executable, str(Path(monitoring.__file__)), '--inbox', str(inbox),
                   '--db', str(db), '--source-id', 'demo', '--once']
        first = subprocess.run(command, capture_output=True, text=True, timeout=10)
        self.assertEqual(first.returncode, 0, first.stderr)
        state = Store(db).read()
        self.assertTrue(state['audit_valid'])
        self.assertEqual(len(state['audit']), 1)
        self.assertEqual(state['audit'][0]['authentication'], {'mode': 'local-service', 'service_id': 'demo'})
        second = subprocess.run(command, capture_output=True, text=True, timeout=10)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(json.loads(second.stdout.splitlines()[-1])['duplicate'], 1)
        self.assertEqual(Store(db).read(), state)

    def test_real_store_concurrent_duplicate_guard_creates_one_batch(self):
        store = Store(self.directory / 'concurrent.sqlite3')
        def submit(_):
            try:
                store.apply('integration/import', self.data,
                            authorize=lambda state: {'mode': 'local-service', 'service_id': 'demo-source'})
                return 200
            except WorkflowError as error:
                return error.status
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(submit, range(2)))
        self.assertEqual(sorted(outcomes), [200, 409])
        state = store.read()
        self.assertTrue(state['audit_valid'])
        self.assertEqual(len(state['audit']), 1)
        self.assertEqual(len(state['integration_batches']), 1)


if __name__ == '__main__':
    unittest.main()
