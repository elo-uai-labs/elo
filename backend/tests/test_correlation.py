import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from domain import Store, WorkflowError
from insights import correlated_cases


class CorrelationTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.store = Store(Path(directory.name) / 'correlation.sqlite3')
        self.store.apply('import', {'actor': 'Analista', 'synthetic': True, 'dataset': {
            'employees': [], 'suppliers': [{'id': 'FOR-AAA', 'name': 'Sintético', 'contact_code': 'FICT-801'}],
            'contracts': []}})
        self.store.apply('detect', {})
        self.state = self.store.apply('detect', {'rule_id': 'supplier-shared-contact'})

    def test_two_rules_one_fact_preserves_state_and_history(self):
        before = deepcopy(self.state)
        result = correlated_cases(self.state, 'ELO-1042')
        self.assertEqual(result['signal_count'], 2)
        self.assertEqual(result['group_count'], 1)
        group = result['groups'][0]
        self.assertEqual(group['case_ids'], ['ELO-1042', 'SIG-SUP-CTR-1042'])
        self.assertEqual(group['contract_id'], 'CTR-1042')
        self.assertEqual(group['distinct_rule_count'], 2)
        self.assertTrue(group['selected'])
        self.assertEqual(self.state, before)
        group['signals'][0]['rule']['id'] = 'changed response'
        self.assertEqual(self.state, before)

    def test_same_contacts_and_risk_do_not_group_other_contract(self):
        other = deepcopy(self.state['cases'][0])
        other['id'] = 'ELO-OTHER'
        other['records']['contract']['id'] = 'CTR-OTHER'
        other['evidence'][0]['id'] = 'CTR-OTHER'
        self.state['cases'].append(other)
        groups = correlated_cases(self.state)['groups']
        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0]['distinct_rule_count'], 2)
        self.assertEqual(groups[1]['case_ids'], ['ELO-OTHER'])

    def test_missing_source_kept_separate_and_unknown_selection_rejected(self):
        self.state['cases'][1]['evidence'] = []
        self.assertEqual(correlated_cases(self.state)['group_count'], 2)
        with self.assertRaises(WorkflowError):
            correlated_cases(self.state, 'ELO-MISSING')
        self.state['audit_valid'] = False
        with self.assertRaises(WorkflowError):
            correlated_cases(self.state)

    def test_existing_human_priority_and_work_are_shared_without_duplication(self):
        self.state['work_items'] = [
            {'id': 'WRK-001', 'title': 'Análise conjunta', 'status': 'in_progress',
             'priority': 'high', 'priority_reason': 'Prazo da análise humana',
             'case_ids': ['ELO-1042', 'SIG-SUP-CTR-1042']},
            {'id': 'WRK-002', 'title': 'Concluído', 'status': 'completed',
             'priority': 'urgent', 'priority_reason': 'Encerrado', 'case_ids': ['ELO-1042']}]
        group = correlated_cases(self.state)['groups'][0]
        self.assertEqual(len(group['work_items']), 2)
        self.assertEqual(group['priority']['value'], 'high')
        self.assertEqual(group['priority']['work_ids'], ['WRK-001'])
        self.assertIn('Prazo da análise humana', group['priority']['reasons'][0])
        self.state['work_items'][0]['status'] = 'cancelled'
        self.assertIsNone(correlated_cases(self.state)['groups'][0]['priority']['value'])

    def test_human_decisions_remain_separate_and_restart_is_stable(self):
        self.state['cases'][0]['decision'] = {'outcome': 'discard', 'reason': 'Revisão humana'}
        group = correlated_cases(self.state)['groups'][0]
        self.assertEqual(group['pending_count'], 1)
        self.assertEqual(group['signals'][0]['decision']['outcome'], 'discard')
        self.assertIsNone(group['signals'][1]['decision'])
        self.assertEqual(correlated_cases(self.store.read()),
                         correlated_cases(Store(self.store.path).read()))

    def test_empty_environment_has_no_groups(self):
        self.state['cases'] = []
        result = correlated_cases(self.state)
        self.assertEqual(result['groups'], [])
        self.assertEqual(result['signal_count'], 0)


if __name__ == '__main__':
    unittest.main()
