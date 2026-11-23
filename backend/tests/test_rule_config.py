import sys
import unittest
from pathlib import Path
from copy import deepcopy
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from domain import DATASET, WorkflowError, initial_state, normalize
from rule_config import defaults, get_config, save, match


class RuleConfigTest(unittest.TestCase):
    def setUp(self):
        self.state = normalize(initial_state())
        self.config = defaults('contact-code-match')
        self.data = {**self.config, 'actor': 'Revisor sintético', 'reason': 'Excluir código administrativo conhecido'}

    def test_filters_change_predictions_without_rewriting_sources(self):
        original = deepcopy(DATASET)
        cases = match(DATASET, 'contact-code-match', self.config)
        self.assertEqual(len(cases), 1)
        code = cases[0]['records']['supplier']['contact_code']
        for changed in ({'excluded_contact_codes': [code]}, {'min_code_length': 160}, {'contract_title_contains': 'inexistente'}, {'enabled': False}):
            self.assertEqual(match(DATASET, 'contact-code-match', {**self.config, **changed}), [])
        self.assertEqual(DATASET, original)
        self.assertEqual(cases[0]['rule']['configuration']['revision'], self.config['revision'])

    def test_version_cas_invalidates_only_requested_scan_preserves_cases(self):
        self.state['detection'] = {'processed_by_rule': {'contact-code-match': ['CTR-1042'], 'supplier-shared-contact': ['CTR-1042']}, 'processed_contract_ids': ['CTR-1042']}
        self.state['cases'] = match(DATASET, 'contact-code-match', self.config)
        before = deepcopy(self.state['cases'])
        save(self.state, {**self.data, 'enabled': False})
        self.assertEqual(get_config(self.state, 'contact-code-match')['version'], 2)
        self.assertNotIn('contact-code-match', self.state['detection']['processed_by_rule'])
        self.assertEqual(self.state['detection']['processed_by_rule']['supplier-shared-contact'], ['CTR-1042'])
        self.assertEqual(self.state['cases'], before)
        with self.assertRaises(WorkflowError): save(self.state, self.data)

    def test_invalid_parameters_do_not_persist(self):
        for changes in ({'enabled': 'true'}, {'min_code_length': True}, {'min_code_length': 0}, {'excluded_contact_codes': ['x', ' x']}, {'excluded_contact_codes': [None]}, {'contract_title_contains': None}, {'rule_id': 'unknown'}):
            before = deepcopy(self.state)
            with self.assertRaises(WorkflowError): save(self.state, {**self.data, **changes})
            self.assertEqual(self.state, before)
