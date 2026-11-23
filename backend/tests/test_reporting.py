import copy
import hashlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dossier
import reporting
from domain import initial_state, match_cases, serialize, WorkflowError


class ReportingTest(unittest.TestCase):
    def setUp(self):
        self.state = initial_state()
        self.state['cases'] = match_cases(self.state['dataset'])
        case = self.state['cases'][0]
        generated = dossier.generate(case['evidence'], 'local')
        generated['revision'] = hashlib.sha256(serialize(generated).encode()).hexdigest()
        case['dossier'] = generated
        case['decision'] = {'actor': 'analyst', 'reason': 'Justificativa humana sintética',
                            'review': 'adjust', 'outcome': 'qualify', 'dossier_revision': generated['revision']}
        self.case = case
        self.create = {'actor': 'compiler', 'title': 'Relatório sintético', 'case_ids': [case['id']]}

    def draft(self):
        reporting.transition(self.state, 'report/create', self.create)
        return self.state['reports'][-1]

    def test_draft_preserves_reviewed_claims_and_sources_without_ai_call(self):
        report = self.draft()
        self.assertEqual(report['status'], 'draft')
        self.assertNotIn('review', report)
        row = report['cases'][0]
        self.assertEqual(row['reviewed_dossier']['prompt_version'], self.case['dossier']['prompt_version'])
        self.assertEqual(row['reviewed_dossier']['limitations'], self.case['dossier']['limitations'])
        self.assertEqual(row['reviewed_dossier']['suggestion'], self.case['dossier']['suggestion'])
        self.assertEqual(row['human_decision']['origin'], 'human')
        self.assertEqual(row['human_decision']['reason'], self.case['decision']['reason'])
        self.assertEqual(row['claims'][0]['text'], self.case['dossier']['claims'][0]['text'])
        self.assertEqual(row['claims'][0]['source_ids'], self.case['dossier']['claims'][0]['source_ids'])
        self.assertEqual(row['sources'][0]['record']['id'], 'CTR-1042')
        self.case['records']['contract']['title'] = 'Alteração posterior'
        self.case['dossier']['claims'][0]['text'] = 'Outra afirmação'
        self.assertNotEqual(row['sources'][0]['record']['title'], 'Alteração posterior')
        self.assertNotEqual(row['claims'][0]['text'], 'Outra afirmação')
        self.assertEqual(report['revision'], reporting.revision(report))

    def test_rejected_suggestion_is_not_reused(self):
        self.case['decision'].update(review='reject', outcome='discard')
        self.case['dossier'].pop('claims')
        self.case['dossier']['prompt_version'] = 'elo-dossier-v2'
        row = self.draft()['cases'][0]
        self.assertEqual(row['claims'], [])
        self.assertEqual(row['claim_status'], 'excluded_by_human_rejection')
        self.assertNotIn('suggestion', row['reviewed_dossier'])
        self.assertNotIn('limitations', row['reviewed_dossier'])
        self.assertEqual(row['human_decision']['outcome'], 'discard')
        self.assertTrue(row['sources'])

    def test_missing_or_unknown_sources_and_legacy_claims_rejected(self):
        for mutate in (
            lambda case: case.update(decision=None),
            lambda case: case['dossier'].pop('claims'),
            lambda case: case['dossier']['claims'][0].update(source_ids=[]),
            lambda case: case['dossier']['claims'][0].update(source_ids=['CTR-UNKNOWN']),
            lambda case: case['dossier']['claims'][0].update(text='EMP-UNKNOWN é aprovador.'),
            lambda case: case['decision'].update(dossier_revision='stale'),
        ):
            state = copy.deepcopy(self.state)
            mutate(state['cases'][0])
            with self.assertRaises(WorkflowError):
                reporting.transition(state, 'report/create', self.create)
            self.assertEqual(state['reports'], [])

    def test_human_review_cas_and_final_immutability(self):
        report = self.draft()
        payload = {'actor': 'reviewer', 'id': report['id'], 'report_revision': report['revision'],
                   'outcome': 'approved', 'reason': 'Fontes e decisões conferidas'}
        before = copy.deepcopy(report)
        for change in ({'report_revision': 'stale'}, {'reason': ' '}, {'actor': ''}):
            with self.assertRaises(WorkflowError):
                reporting.transition(self.state, 'report/review', {**payload, **change})
            self.assertEqual(report, before)
        reporting.transition(self.state, 'report/review', payload)
        self.assertEqual(report['status'], 'approved')
        self.assertEqual(report['review']['reviewed_revision'], before['revision'])
        final = copy.deepcopy(report)
        with self.assertRaises(WorkflowError):
            reporting.transition(self.state, 'report/review', {**payload, 'report_revision': report['revision'], 'outcome': 'rejected'})
        self.assertEqual(report, final)

    def test_rejection_is_terminal_and_selection_bounded(self):
        for identifiers in ([], [self.case['id']] * 2, ['missing'], ['X'] * 21):
            with self.assertRaises(WorkflowError):
                reporting.transition(self.state, 'report/create', {**self.create, 'case_ids': identifiers})
        report = self.draft()
        payload = {'actor': 'reviewer', 'id': report['id'], 'report_revision': report['revision'],
                   'outcome': 'rejected', 'reason': 'Revisar fundamentação em novo rascunho'}
        reporting.transition(self.state, 'report/review', payload)
        self.assertEqual(report['status'], 'rejected')
        with self.assertRaises(WorkflowError):
            reporting.transition(self.state, 'report/review', {**payload, 'report_revision': report['revision']})


if __name__ == '__main__':
    unittest.main()
