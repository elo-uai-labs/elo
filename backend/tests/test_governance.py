import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dossier
from domain import Store, WorkflowError


class GovernanceTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.store = Store(Path(folder.name) / 'state.sqlite3')
        self.human = {'actor': 'Analista', 'reason': 'Evidências revistas'}

    def create_risk(self):
        return self.store.apply('risk/save', {**self.human, 'name': 'Risco sintético adicional', 'level': 'Baixa', 'control_ids': ['CTL-001']})['risks'][-1]

    def qualify(self):
        state = self.store.apply('detect', {})
        state = self.store.apply('dossier', dossier.generate(state['case']['evidence'], 'local'))
        return self.store.apply('decision', {**self.human, 'review': 'accept', 'outcome': 'qualify', 'dossier_revision': state['case']['dossier']['revision']})

    def test_catalog_cas_archive_and_atomic_validation(self):
        risk = self.create_risk()
        updated = self.store.apply('risk/save', {**self.human, **risk, 'level': 'Alta'})['risks'][-1]
        with self.assertRaises(WorkflowError):
            self.store.apply('risk/save', {**self.human, **risk, 'level': 'Crítica'})
        self.store.apply('catalog/archive', {**self.human, 'kind': 'risk', 'id': updated['id'], 'revision': updated['revision']})
        with self.assertRaises(WorkflowError):
            self.store.apply('risk/save', {**self.human, **self.store.read()['risks'][-1]})
        self.assertTrue(self.store.read()['audit_valid'])
        self.assertEqual(len(self.store.read()['audit']), 3)

    def test_archived_control_link_can_be_retained_but_not_added(self):
        control = self.store.read()['controls'][0]
        self.store.apply('catalog/archive', {**self.human, 'kind': 'control', 'id': control['id'], 'revision': control['revision']})
        risk = self.store.read()['risks'][0]
        state = self.store.apply('risk/save', {**self.human, **risk, 'name': 'Risco renomeado mantendo histórico'})
        self.assertIn(control['id'], state['risks'][0]['control_ids'])
        with self.assertRaises(WorkflowError):
            self.store.apply('risk/save', {**self.human, 'name': 'Novo risco', 'level': 'Baixa', 'control_ids': [control['id']]})
        risk = self.store.read()['risks'][0]
        self.store.apply('risk/save', {**self.human, **risk, 'control_ids': []})
        risk = self.store.read()['risks'][0]
        with self.assertRaises(WorkflowError):
            self.store.apply('risk/save', {**self.human, **risk, 'control_ids': [control['id']]})
        self.assertTrue(self.store.read()['audit_valid'])

    def test_case_links_change_impact_target_only(self):
        risk = self.create_risk()
        self.store.apply('detect', {})
        self.store.apply('case/link', {**self.human, 'case_id': 'ELO-1042', 'linkage_revision': self.store.read()['case']['linkage_revision'], 'risk_id': risk['id'], 'dimension_id': 'DIM-001'})
        state = self.store.read()
        self.assertEqual(state['risk']['id'], risk['id'])
        state = self.store.apply('dossier', dossier.generate(state['case']['evidence'], 'local'))
        state = self.store.apply('decision', {**self.human, 'review': 'adjust', 'outcome': 'qualify', 'dossier_revision': state['case']['dossier']['revision'], 'linkage_revision': state['case']['linkage_revision']})
        self.assertEqual(state['case']['impacts'][0]['target_id'], risk['id'])
        state = self.store.apply('impact', {**self.human, 'kind': 'risk', 'outcome': 'approved'})
        self.assertEqual(state['risk']['level'], 'Alta')
        self.assertEqual(state['risks'][0]['level'], 'Moderada')
        with self.assertRaises(WorkflowError):
            self.store.apply('case/link', {**self.human, 'case_id': 'ELO-1042', 'risk_id': 'RSK-001', 'dimension_id': 'DIM-001'})

    def test_stale_case_links_and_decision_cannot_overwrite(self):
        risk = self.create_risk()
        state = self.store.apply('detect', {})
        state = self.store.apply('dossier', dossier.generate(state['case']['evidence'], 'local'))
        old_revision = state['case']['linkage_revision']
        link = {**self.human, 'case_id': 'ELO-1042', 'risk_id': risk['id'], 'dimension_id': 'DIM-001', 'linkage_revision': old_revision}
        self.store.apply('case/link', link)
        with self.assertRaises(WorkflowError):
            self.store.apply('case/link', {**link, 'risk_id': 'RSK-001'})
        decision = {**self.human, 'outcome': 'qualify', 'review': 'accept', 'dossier_revision': state['case']['dossier']['revision']}
        with self.assertRaises(WorkflowError):
            self.store.apply('decision', decision)
        with self.assertRaises(WorkflowError):
            self.store.apply('decision', {**decision, 'linkage_revision': old_revision})
        state = self.store.apply('decision', {**decision, 'linkage_revision': self.store.read()['case']['linkage_revision']})
        self.assertEqual(state['case']['impacts'][0]['target_id'], risk['id'])

    def test_qualifying_signal_never_downgrades_critical_risk(self):
        risk = self.store.read()['risks'][0]
        self.store.apply('risk/save', {**self.human, **risk, 'level': 'Crítica'})
        state = self.qualify()
        self.assertEqual(state['case']['impacts'][0]['proposed_level'], 'Crítica')
        state = self.store.apply('impact', {**self.human, 'kind': 'risk', 'outcome': 'approved'})
        self.assertEqual(state['risk']['level'], 'Crítica')

    def test_legacy_pending_impact_captures_revision_before_catalog_mutation(self):
        from domain import initial_state, transition
        state = initial_state()
        transition(state, 'detect', {})
        transition(state, 'dossier', dossier.generate(state['case']['evidence'], 'local'))
        transition(state, 'decision', {**self.human, 'outcome': 'qualify', 'review': 'accept', 'dossier_revision': state['case']['dossier']['revision']})
        for impact in state['case']['impacts']:
            impact.pop('target_id')
            impact.pop('target_revision')
        control = state['controls'][0]
        transition(state, 'control/save', {**self.human, **control, 'description': 'Descrição alterada após proposta legada'})
        with self.assertRaises(WorkflowError):
            transition(state, 'impact', {**self.human, 'kind': 'risk', 'outcome': 'approved'})
        self.assertEqual(state['risk']['level'], 'Moderada')

    def test_changed_control_invalidates_impact_revision(self):
        state = self.qualify()
        control = state['controls'][0]
        self.store.apply('control/save', {**self.human, **control, 'name': 'Controle alterado'})
        with self.assertRaises(WorkflowError):
            self.store.apply('impact', {**self.human, 'kind': 'risk', 'outcome': 'approved'})
        self.assertEqual(self.store.read()['case']['impacts'][0]['status'], 'pending')
        self.store.apply('impact', {**self.human, 'kind': 'risk', 'outcome': 'rejected'})

    def test_weighted_assessment_evidence_gaps_and_version(self):
        state = self.store.read()
        dimension = state['dimensions'][0]
        dimension = self.store.apply('dimension/save', {**self.human, **dimension, 'questions': [
            {'id': 'Q1', 'text': 'Controle A', 'weight': 3, 'max_score': 4},
            {'id': 'Q2', 'text': 'Controle B', 'weight': 1, 'max_score': 2}]})['dimensions'][0]
        payload = {**self.human, 'dimension_id': dimension['id'], 'dimension_revision': dimension['revision'], 'confirmed': True,
                   'answers': [{'question_id': 'Q1', 'score': 4, 'evidence': 'Ata fictícia A'}, {'question_id': 'Q2', 'score': 0, 'evidence': 'Ausência documentada B'}]}
        state = self.store.apply('maturity/assess', payload)
        assessment = state['assessments'][0]
        self.assertEqual(assessment['score'], 75)
        self.assertEqual(assessment['level'], 'Intermediária')
        self.assertEqual(assessment['answers'][1]['gap'], 2)
        with self.assertRaises(WorkflowError):
            self.store.apply('maturity/assess', payload)
        dimension = state['dimensions'][0]
        self.store.apply('dimension/save', {**self.human, **dimension, 'questions': [{'id': 'Q3', 'text': 'Nova pergunta', 'weight': 1, 'max_score': 3}]})
        state = self.store.read()
        self.assertEqual(state['dimensions'][0]['level'], 'Reavaliação necessária')
        self.assertEqual(state['assessments'][0]['questions'][0]['id'], 'Q1')

    def test_invalid_assessments_never_write(self):
        dimension = self.store.read()['dimensions'][0]
        before = self.store.export_state()
        payload = {**self.human, 'dimension_id': dimension['id'], 'dimension_revision': dimension['revision'], 'confirmed': True,
                   'answers': [{'question_id': 'Q1', 'score': 4, 'evidence': 'Ata'}, {'question_id': 'Q2', 'score': 0, 'evidence': 'Ausência'}]}
        for key, value in [('confirmed', False), ('answers', []), ('answers', [{'question_id': 'Q1', 'score': 10, 'evidence': 'Ata'}, {'question_id': 'Q2', 'score': 0, 'evidence': 'Ausência'}])]:
            with self.assertRaises(WorkflowError):
                self.store.apply('maturity/assess', {**payload, key: value})
            self.assertEqual(self.store.export_state(), before)

    def test_closure_requires_independent_human_and_current_revision(self):
        self.qualify()
        state = self.store.apply('action', {**self.human, 'title': 'Rever diligência', 'owner': 'Executor', 'due': '2027-01-01'})
        action = state['actions'][0]
        payload = {**self.human, 'id': action['id'], 'action_revision': action['revision'], 'title': 'Revisar evidências', 'owner': 'Executor B', 'due': '2027-02-01'}
        state = self.store.apply('action/edit', payload)
        with self.assertRaises(WorkflowError):
            self.store.apply('action/edit', payload)
        action = state['actions'][0]
        state = self.store.apply('action/update', {'actor': 'Executor', 'id': action['id'], 'action_revision': action['revision'], 'status': 'closure_requested', 'evidence': 'Ata sintética executada'})
        action = state['actions'][0]
        payload = {'actor': 'executor', 'id': action['id'], 'action_revision': action['revision'], 'outcome': 'approved', 'reason': 'Conferido'}
        with self.assertRaises(WorkflowError):
            self.store.apply('action/close', payload)
        state = self.store.apply('action/close', {**payload, 'actor': 'Revisor', 'outcome': 'rejected'})
        self.assertEqual(state['actions'][0]['status'], 'in_progress')
        action = state['actions'][0]
        state = self.store.apply('action/update', {'actor': 'Executor', 'id': action['id'], 'action_revision': action['revision'], 'status': 'done', 'evidence': 'Ata corrigida'})
        action = state['actions'][0]
        state = self.store.apply('action/close', {**payload, 'actor': 'Revisor', 'action_revision': action['revision']})
        self.assertEqual(state['actions'][0]['status'], 'done')
        with self.assertRaises(WorkflowError):
            self.store.apply('action/edit', {**payload, 'action_revision': state['actions'][0]['revision']})
        self.assertTrue(state['audit_valid'])


if __name__ == '__main__':
    unittest.main()
