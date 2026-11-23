import copy
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import work
from domain import Store, WorkflowError


class WorkTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / 'work.sqlite3'
        self.store = Store(self.path)
        self.data = {'actor': 'Planejador', 'reason': 'Planejamento aprovado', 'title': 'Revisão temática de diligência',
            'description': 'Examinar evidências sintéticas de diligência da segunda linha.', 'owner': 'Executor',
            'due': '2027-02-01', 'priority': 'high', 'priority_reason': 'Prazo institucional próximo', 'case_ids': []}

    def create(self, at='2027-01-01T12:00:00+00:00', **changes):
        with patch('work.utc_now', return_value=datetime.fromisoformat(at)):
            return self.store.apply('work/create', {**self.data, **changes})['work_items'][-1]

    def status(self, item, status, at, **changes):
        with patch('work.utc_now', return_value=datetime.fromisoformat(at)):
            return self.store.apply('work/status', {'actor': 'Executor', 'reason': 'Registro humano do andamento',
                'id': item['id'], 'revision': item['revision'], 'status': status, **changes})['work_items'][0]

    def test_independent_lifecycle_result_and_restart(self):
        item = self.create()
        self.assertIsNone(self.store.read()['case'])
        self.assertEqual(item['case_ids'], [])
        with self.assertRaises(WorkflowError):
            self.status(item, 'completed', '2027-01-01T13:00:00+00:00', result='Resultado prematuro')
        item = self.status(item, 'in_progress', '2027-01-02T12:00:00+00:00')
        with self.assertRaises(WorkflowError):
            self.status(item, 'completed', '2027-01-04T12:00:00+00:00', result=' ')
        item = self.status(item, 'completed', '2027-01-04T12:00:00+00:00', result='Revisão humana concluída; duas lacunas documentadas.')
        self.assertEqual(item['completed_at'], '2027-01-04T12:00:00.000+00:00')
        self.assertTrue(item['result'])
        with self.assertRaises(WorkflowError):
            self.store.apply('work/update', {**self.data, 'id': item['id'], 'revision': item['revision']})
        state = Store(self.path).read()
        self.assertEqual(state['work_items'][0], item)
        self.assertTrue(state['audit_valid'])
        self.assertEqual(len(state['audit']), 3)

    def test_atomic_fields_references_justification_and_cas(self):
        initial = self.store.export_state()
        for changes in ({'reason': ''}, {'priority_reason': ''}, {'case_ids': ['missing']}, {'case_ids': ['a', 'a']},
                        {'due': '2027-02-30'}, {'priority': 'AI-high'}, {'description': ''}):
            with self.assertRaises(WorkflowError):
                self.create(**changes)
            self.assertEqual(self.store.export_state(), initial)
        self.store.apply('detect', {})
        item = self.create(case_ids=['ELO-1042'])
        payload = {**self.data, 'id': item['id'], 'revision': item['revision'], 'case_ids': ['ELO-1042'], 'owner': 'Outro executor'}
        state = self.store.apply('work/update', payload)
        self.assertEqual(state['work_items'][0]['owner'], 'Outro executor')
        with self.assertRaises(WorkflowError):
            self.store.apply('work/update', {**payload, 'priority': 'urgent'})
        self.assertEqual(self.store.read()['work_items'][0]['priority'], 'high')

    def test_concurrent_updates_one_revision_wins(self):
        item = self.create()
        def update(index):
            try:
                self.store.apply('work/update', {**self.data, 'id': item['id'], 'revision': item['revision'], 'title': f'Trabalho {index}'})
                return 200
            except WorkflowError as error:
                return error.status
        with ThreadPoolExecutor(max_workers=4) as pool:
            statuses = list(pool.map(update, range(4)))
        self.assertEqual(statuses.count(200), 1)
        self.assertEqual(statuses.count(409), 3)
        self.assertEqual(len(self.store.read()['audit']), 2)

    def test_summary_denominators_durations_priorities_and_timezone(self):
        first = self.create()
        first = self.status(first, 'in_progress', '2027-01-02T12:00:00+00:00')
        self.status(first, 'completed', '2027-01-04T12:00:00+00:00', result='Conclusão humana documentada')
        cancelled = self.create(priority='urgent')
        self.store.apply('work/status', {'actor': 'Gestor', 'reason': 'Escopo cancelado pelo responsável', 'id': cancelled['id'], 'revision': cancelled['revision'], 'status': 'cancelled'})
        self.create(priority='low', due='2027-01-03')
        self.create(priority='normal', due='2027-01-04')
        state = self.store.read()
        # 02:00 UTC is still January 3 in São Paulo: due Jan 3 is not overdue yet.
        report = work.summary(state, datetime(2027, 1, 4, 2, tzinfo=timezone.utc))
        self.assertEqual(report['today'], '2027-01-03')
        self.assertEqual(report['overdue'], 0)
        report = work.summary(state, datetime(2027, 1, 4, 12, tzinfo=timezone.utc))
        self.assertEqual(report['total'], 4)
        self.assertEqual(report['pending'], 2)
        self.assertEqual(report['overdue'], 1)
        self.assertEqual(report['completion_rate']['numerator'], 1)
        self.assertEqual(report['completion_rate']['denominator'], 3)
        self.assertEqual(report['treatment_time']['completed_with_timing'], 1)
        self.assertEqual(report['treatment_time']['mean_seconds'], 172800)
        self.assertEqual(report['lead_time']['mean_seconds'], 259200)
        self.assertEqual(next(row for row in report['by_priority'] if row['priority'] == 'low')['overdue'], 1)
        self.assertEqual(self.store.read(), state)

    def test_empty_summary_and_additive_read_migration(self):
        before = self.store.export_state()
        self.assertNotIn('work_items', before)
        report = work.summary(self.store.read())
        self.assertIsNone(report['completion_rate']['percent'])
        self.assertIsNone(report['treatment_time']['mean_seconds'])
        self.assertEqual(report['completion_rate']['denominator'], 0)
        self.assertEqual(self.store.export_state(), before)
        broken = copy.deepcopy(self.store.read())
        broken['audit_valid'] = False
        with self.assertRaises(WorkflowError):
            work.summary(broken)


if __name__ == '__main__':
    unittest.main()
