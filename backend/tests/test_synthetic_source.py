import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from domain import Store
from synthetic_source import SourceError, ingest, validate_endpoint

ROOT = Path(__file__).resolve().parents[2]
TOKEN = 'synthetic-transport-test'


class SyntheticSourceTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='elo-http-source-')
        self.addCleanup(temp.cleanup)
        self.store = Store(Path(temp.name) / 'destination.sqlite3')

    def source(self, scenario='success'):
        process = subprocess.Popen([sys.executable, str(ROOT/'scripts/trl-source-server.py'), '--scenario', scenario],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            env={**os.environ, 'ELO_SYNTHETIC_SOURCE_TOKEN': TOKEN})
        def stop():
            process.terminate()
            try:
                process.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill(); process.communicate(timeout=3)
        self.addCleanup(stop)
        info = json.loads(process.stdout.readline())
        self.assertNotEqual(info['pid'], os.getpid())
        return f'http://127.0.0.1:{info["port"]}/snapshot'

    def test_paged_service_import_reconcile_and_restart_idempotence(self):
        endpoint = self.source()
        result = ingest(self.store, endpoint, TOKEN, 'http-test')
        self.assertEqual(result['status'], 'processed')
        self.assertEqual(result['pages'], 2)
        self.assertEqual(result['record_ids']['contracts'], ['CTR-HTTP'])
        state = self.store.export_state()
        self.assertTrue(state['audit_valid'])
        self.assertIn('ELO-HTTP', [case['id'] for case in state['cases']])
        event = state['audit'][-1]
        self.assertEqual(event['authentication'], {'mode': 'local-service', 'service_id': 'http-test'})
        self.assertEqual(event['details']['source_name'], 'http-sample-v1.json')
        again = ingest(Store(self.store.path), endpoint, TOKEN, 'http-test')
        self.assertEqual(again['status'], 'duplicate')
        self.assertEqual(self.store.export_state(), state)
        self.assertNotIn(TOKEN, json.dumps(state))

    def test_transient_503_and_timeout_retry_are_bounded(self):
        for scenario in ('retry503', 'timeout'):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as temp:
                store = Store(Path(temp)/'retry.sqlite3')
                result = ingest(store, self.source(scenario), TOKEN, scenario, timeout=.1)
                self.assertEqual(result['attempts'], 3)
                self.assertEqual(result['status'], 'processed')

    def test_failures_never_publish_partial_pages(self):
        for scenario in ('unauthorized', 'always503', 'schema', 'drift', 'duplicate', 'missing-reference', 'counts', 'oversized', 'redirect'):
            with self.subTest(scenario=scenario):
                before = self.store.export_state()
                with self.assertRaises(SourceError) as error:
                    ingest(self.store, self.source(scenario), TOKEN, 'fault-test')
                self.assertEqual(self.store.export_state(), before)
                self.assertNotIn(TOKEN, str(error.exception))

    def test_concurrent_import_is_one_atomic_batch(self):
        endpoint = self.source()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: ingest(self.store, endpoint, TOKEN, 'concurrent'), range(2)))
        self.assertEqual(sorted(row['status'] for row in results), ['duplicate', 'processed'])
        state = self.store.export_state()
        self.assertEqual(len(state['integration_batches']), 1)
        self.assertEqual(len(state['audit']), 1)
        self.assertTrue(state['audit_valid'])

    def test_endpoint_contract_cannot_target_external_or_redirect_hosts(self):
        for value in ('https://127.0.0.1:80/snapshot', 'http://localhost:80/snapshot', 'http://example.com:80/snapshot',
                      'http://127.0.0.1:80/snapshot?next=secret', 'http://user:secret@127.0.0.1:80/snapshot',
                      'http://127.0.0.1:80/other', 'http://127.0.0.2:80/snapshot', 'http://127.0.0.1:0/snapshot'):
            with self.subTest(endpoint=value), self.assertRaises(SourceError):
                validate_endpoint(value)
        self.assertEqual(validate_endpoint('http://127.0.0.1:8123/snapshot'), 'http://127.0.0.1:8123/snapshot')

    def test_cli_rejects_manual_database_before_initializing(self):
        result = subprocess.run([sys.executable, str(ROOT/'backend/synthetic_source.py'), '--endpoint', 'http://127.0.0.1:1/snapshot',
            '--source-id', 'test', '--db', str(ROOT/'data/elo.sqlite3'), '--synthetic'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('fora de data/', result.stderr)


if __name__ == '__main__':
    unittest.main()
