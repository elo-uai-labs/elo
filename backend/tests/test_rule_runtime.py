import copy
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from domain import Store, WorkflowError
from rule_config import get_config


class RuleRuntimeTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.store = Store(Path(folder.name) / 'rules.sqlite3')

    def configure(self, rule_id='contact-code-match', **changes):
        config = get_config(self.store.read(), rule_id)
        return self.store.apply('rule/config', {**config, **changes, 'actor': 'Revisor', 'reason': 'Calibração humana no gabarito sintético'})

    def test_config_blocks_disabled_execution_and_is_audited(self):
        self.configure(enabled=False)
        before = self.store.export_state()
        with self.assertRaises(WorkflowError):
            self.store.apply('detect', {})
        self.assertEqual(self.store.export_state(), before)
        self.assertEqual(before['audit'][-1]['action'], 'Parâmetros da regra atualizados')
        self.assertEqual(self.store.read()['rules'][0]['configuration']['version'], 2)

    def test_rescan_preserves_cases_and_other_rule_processed_state(self):
        first = self.store.apply('detect', {})['case']
        self.store.apply('detect', {'rule_id': 'supplier-shared-contact'})
        secondary_before = copy.deepcopy(self.store.read()['detection']['processed_by_rule']['supplier-shared-contact'])
        self.configure(excluded_contact_codes=['FICT-801'])
        state = self.store.read()
        self.assertEqual(state['detection']['processed_by_rule']['supplier-shared-contact'], secondary_before)
        self.assertEqual(state['rules'][0]['pending_count'], 2)
        state = self.store.apply('detect', {})
        self.assertEqual(state['cases'], [first])
        self.assertEqual(state['audit'][-1]['details']['case_ids'], [])
        self.assertEqual(first['rule']['configuration']['version'], 1)
        self.assertEqual(state['audit'][-1]['details']['rule']['configuration']['version'], 2)
        self.assertTrue(state['audit_valid'])

    def test_new_case_snapshot_configuration_and_filter_enable(self):
        self.configure(min_code_length=160)
        state = self.store.apply('detect', {})
        self.assertEqual(state['cases'], [])
        self.configure(min_code_length=1, contract_title_contains='MANUTENÇÃO')
        state = self.store.apply('detect', {})
        self.assertEqual(len(state['cases']), 1)
        self.assertEqual(state['cases'][0]['rule']['configuration']['version'], 3)
        self.assertEqual(state['cases'][0]['records']['contract']['title'], 'Serviços de manutenção')

    def test_monitoring_imports_but_explicitly_skips_disabled_rules(self):
        self.configure(enabled=False)
        self.configure('supplier-shared-contact', enabled=False)
        batch = {'source_id': 'synthetic-monitor', 'source_name': 'batch.json', 'payload': {'synthetic': True, 'dataset': {
            'employees': [], 'suppliers': [], 'contracts': [{'id': 'CTR-MON', 'supplier_id': 'FOR-031', 'approver_id': 'EMP-014', 'title': 'Contrato sintético'}]}}}
        state = self.store.apply('integration/import', batch)
        self.assertEqual(len(state['dataset']['contracts']), 3)
        self.assertEqual(state['cases'], [])
        self.assertEqual(state['integration_batches'][0]['skipped_rule_ids'], ['contact-code-match', 'supplier-shared-contact'])
        self.assertEqual(state['integration_batches'][0]['rules'], [])
        self.assertTrue(state['audit_valid'])


if __name__ == '__main__':
    unittest.main()
