import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dossier
from domain import DATASET, Store, WorkflowError, match_supplier_cases


class SupplierRuleTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.store = Store(Path(folder.name) / 'rules.sqlite3')
        self.rule = {'rule_id': 'supplier-shared-contact'}

    def import_supplier(self, identifier='FOR-AAA', code='FICT-801'):
        return self.store.apply('import', {'actor': 'Analista', 'synthetic': True, 'dataset': {
            'employees': [], 'suppliers': [{'id': identifier, 'name': 'Fornecedor fictício', 'contact_code': code}], 'contracts': []}})

    def test_empty_self_and_distinct_codes_do_not_match(self):
        self.assertEqual(match_supplier_cases(deepcopy(DATASET)), [])
        dataset = deepcopy(DATASET)
        for supplier in dataset['suppliers']:
            supplier['contact_code'] = ''
        self.assertEqual(match_supplier_cases(dataset), [])

    def test_secondary_explicit_primary_unchanged_and_no_duplicate_cases(self):
        self.import_supplier()
        state = self.store.apply('detect', {})
        self.assertEqual([case['id'] for case in state['cases']], ['ELO-1042'])
        primary = deepcopy(state['case'])
        state = self.store.apply('detect', self.rule)
        case = state['cases'][1]
        self.assertEqual(case['id'], 'SIG-SUP-CTR-1042')
        self.assertEqual(case['title'], 'Cadastro compartilhado entre fornecedores')
        self.assertEqual([row['id'] for row in case['evidence']], ['CTR-1042', 'FOR-031', 'FOR-AAA'])
        self.assertNotIn('employee', case['records'])
        self.assertNotIn('EMP-', ' '.join(row['detail'] for row in case['evidence']))
        self.assertEqual(state['cases'][0], primary)
        with self.assertRaises(WorkflowError):
            self.store.apply('detect', self.rule)
        self.assertTrue(self.store.read()['audit_valid'])

    def test_new_supplier_invalidates_old_secondary_scan_only(self):
        state = self.store.apply('detect', self.rule)
        self.assertEqual(state['cases'], [])
        self.assertEqual(state['detection']['processed_contract_ids'], [])
        self.store.apply('detect', {})
        state = self.import_supplier()
        self.assertEqual(state['detection']['processed_by_rule']['supplier-shared-contact'], [])
        self.assertEqual(len(state['detection']['processed_contract_ids']), 2)
        state = self.store.apply('detect', self.rule)
        self.assertEqual(len(state['cases']), 2)
        old_case = deepcopy(state['cases'][1])
        self.import_supplier('FOR-AAB')
        state = self.store.apply('detect', self.rule)
        self.assertEqual(len(state['cases']), 2)
        self.assertEqual(state['cases'][1], old_case)
        self.assertEqual(state['audit'][-1]['details']['case_ids'], [])

    def test_lexical_source_choice_and_generic_dossier_impacts(self):
        self.import_supplier('FOR-ZZZ')
        self.import_supplier('FOR-AAA')
        state = self.store.apply('detect', self.rule)
        case = state['case']
        self.assertEqual(case['evidence'][-1]['id'], 'FOR-AAA')
        generated = dossier.generate(case['evidence'], 'local', rule_id=self.rule['rule_id'])
        self.assertNotIn('EMP-', generated['text'])
        state = self.store.apply('dossier', {**generated, 'case_id': case['id']})
        state = self.store.apply('decision', {'case_id': case['id'], 'actor': 'Analista', 'review': 'adjust', 'outcome': 'qualify', 'reason': 'Verificar contexto', 'dossier_revision': state['case']['dossier']['revision']})
        self.assertTrue(all('aprovador' not in item['rationale'].lower() for item in state['case']['impacts']))
        self.assertIn('fornecedores', state['case']['impacts'][0]['rationale'])
        self.assertEqual(state['case']['impacts'][0]['label'], 'Reavaliar risco associado')

    def test_legacy_detection_maps_primary_only(self):
        from domain import initial_state, normalize, match_case
        state = initial_state()
        state['case'] = match_case(state['dataset'])
        normalize(state)
        self.assertEqual(state['detection']['processed_by_rule'], {'contact-code-match': ['CTR-1042', 'CTR-1091']})


if __name__ == '__main__':
    unittest.main()
