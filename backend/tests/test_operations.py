import copy
from datetime import datetime, timezone
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import work
from domain import WorkflowError


class OperationsTest(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 23, 3, tzinfo=timezone.utc)
        self.state = {'audit_valid': True, 'work_items': [], 'actions': [], 'cases': []}

    def item(self, identifier, due, status='planned', completed_at=None):
        return {'id': identifier, 'title': identifier, 'owner': 'Operadora', 'due': due,
                'status': status, 'priority': 'normal', 'completed_at': completed_at}

    def report(self):
        before = copy.deepcopy(self.state)
        result = work.summary(self.state, self.now)['operations']
        self.assertEqual(self.state, before)
        return result

    def test_notifications_calendar_boundaries_dedup_and_resolved(self):
        self.state['work_items'] = [self.item('WRK-001', '2026-11-22'), self.item('WRK-002', '2026-11-23'),
            self.item('WRK-003', '2026-11-30'), self.item('WRK-004', '2026-12-01'),
            self.item('WRK-005', '2026-11-01', 'cancelled')]
        rows = self.report()['notifications']
        self.assertEqual([r['kind'] for r in rows], ['overdue', 'due_today', 'due_soon'])
        self.assertEqual([r['days_to_due'] for r in rows], [-1, 0, 7])
        self.assertEqual(rows, self.report()['notifications'])
        self.state['work_items'][0]['status'] = 'completed'
        self.assertEqual(self.report()['notification_total'], 2)
        # Before local midnight, November 23 is tomorrow, not today.
        self.now = datetime(2026, 11, 23, 2, 59, tzinfo=timezone.utc)
        self.assertEqual(self.report()['notifications'][0]['kind'], 'due_soon')

    def test_closure_notice_independent_of_deadline_and_closed_removed(self):
        self.state['actions'] = [{**self.item('REC-001', '2027-01-01', 'closure_requested'), 'case_id': 'ELO-1'}]
        rows = self.report()['notifications']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['kind'], 'closure_review')
        self.state['actions'][0]['status'] = 'done'
        self.assertEqual(self.report()['notifications'], [])

    def test_sla_timezone_null_exclusions_and_current_deadline(self):
        self.state['work_items'] = [self.item('1', '2026-11-22', 'completed', '2026-11-23T02:59:59+00:00'),
            self.item('2', '2026-11-22', 'completed', '2026-11-23T03:00:00+00:00'),
            self.item('3', '2026-11-22', 'completed', None), self.item('4', '2026-11-22', 'cancelled'),
            self.item('5', '2026-11-22')]
        sla = self.report()['sla']
        self.assertEqual((sla['on_time'], sla['evaluated'], sla['missing_timestamp'], sla['percent']), (1, 2, 1, 50))
        self.state['work_items'][1]['due'] = '2026-11-23'
        self.assertEqual(self.report()['sla']['percent'], 100)
        self.state['work_items'] = []
        self.assertIsNone(self.report()['sla']['percent'])

    def case(self, id, contract, rule='rule-a', supplier='FOR-1', evidence=True):
        return {'id': id, 'rule': {'id': rule}, 'records': {'contract': {'id': contract, 'supplier_id': supplier}},
                'evidence': [{'id': contract}] if evidence else []}

    def test_recurrence_requires_distinct_evidenced_contracts_same_rule_supplier(self):
        self.state['cases'] = [self.case('1', 'CTR-1'), self.case('2', 'CTR-1'), self.case('3', 'CTR-2', 'rule-b'),
                               self.case('4', 'CTR-2', supplier='FOR-2'), self.case('5', 'CTR-3', evidence=False)]
        self.assertEqual(self.report()['recurrence']['groups'], [])
        self.state['cases'].append(self.case('6', 'CTR-4'))
        group = self.report()['recurrence']['groups'][0]
        self.assertEqual(group['contract_ids'], ['CTR-1', 'CTR-4'])
        self.assertEqual(group['distinct_contracts'], 2)

    def test_invalid_audit_blocks_all_operations(self):
        self.state['audit_valid'] = False
        with self.assertRaises(WorkflowError): self.report()
