"""Incremental synthetic imports, independent cases and legacy hash compatibility."""
import hashlib
import json
import sqlite3
import sys
import tempfile
import unittest
from copy import deepcopy
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dossier
from domain import Store, WorkflowError, initial_state, serialize, transition


class MultiCaseTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / 'test.sqlite3'
        self.store = Store(self.path)

    def batch(self, match=True):
        return {'actor': 'Importador sintético', 'synthetic': True, 'dataset': {
            'employees': [{'id': 'EMP-B', 'name': 'Pessoa B fictícia', 'role': 'Aprovador', 'contact_code': 'SYN-B'}],
            'suppliers': [{'id': 'FOR-B', 'name': 'Fornecedor B fictício', 'contact_code': 'SYN-B' if match else 'SYN-C'}],
            'contracts': [{'id': 'CTR-B', 'title': 'Contrato sintético B', 'approver_id': 'EMP-B', 'supplier_id': 'FOR-B'}]}}

    def test_incremental_import_preserves_decisions_and_sources(self):
        first = self.store.apply('detect', {})['case']
        self.store.apply('dossier', dossier.generate(first['evidence'], 'local'))
        first = self.store.read()['case']
        self.store.apply('decision', {'actor': 'Revisor', 'reason': 'Acompanhar', 'review': 'adjust', 'outcome': 'monitor', 'dossier_revision': first['dossier']['revision']})
        before = deepcopy(self.store.read()['case'])
        self.store.apply('import', self.batch())
        state = self.store.apply('detect', {})
        self.assertEqual(len(state['cases']), 2)
        self.assertEqual(state['cases'][0], before)
        selected = self.store.read('ELO-B')['case']
        self.assertEqual(selected['records']['contract']['id'], 'CTR-B')
        self.store.apply('dossier', {**dossier.generate(selected['evidence'], 'local'), 'case_id': 'ELO-B'})
        self.assertIsNotNone(self.store.read('ELO-B')['case']['dossier'])
        self.assertEqual(self.store.read()['case'], before)
        self.assertTrue(Store(self.path).read()['audit_valid'])
        with self.assertRaises(WorkflowError):
            self.store.apply('detect', {})
        self.assertEqual(len(self.store.read()['cases']), 2)

    def test_no_match_is_success_and_audited(self):
        self.store.apply('detect', {})
        self.store.apply('import', self.batch(match=False))
        state = self.store.apply('detect', {})
        self.assertEqual(len(state['cases']), 1)
        self.assertEqual(state['audit'][-1]['details']['case_ids'], [])
        self.assertEqual(state['audit'][-1]['action'], 'Análise concluída sem novos indícios')
        self.assertTrue(state['audit_valid'])
        # An initially empty synthetic environment also completes with no signal.
        initial = initial_state()
        initial['dataset']['contracts'] = []
        transition(initial, 'detect', {})
        self.assertEqual(initial['cases'], [])
        self.assertEqual(initial['detection']['matches'], 0)

    def test_import_validation_atomicity(self):
        original = self.store.read()
        for alter in (
            lambda b: b.update(synthetic=False),
            lambda b: b['dataset']['contracts'][0].update(approver_id='EMP-MISSING'),
            lambda b: b['dataset']['employees'].append(deepcopy(b['dataset']['employees'][0])),
            lambda b: b['dataset']['contracts'][0].update(id='CTR-1042'),
            lambda b: b['dataset'].update(extra=[]),
            lambda b: b['dataset']['employees'][0].update(name=123),
        ):
            batch = self.batch()
            alter(batch)
            with self.assertRaises(WorkflowError):
                self.store.apply('import', batch)
            self.assertEqual(self.store.read(), original)

    def test_cross_case_action_update_rejected(self):
        self.store.apply('import', self.batch())
        self.store.apply('detect', {})
        for identifier in ('ELO-1042', 'ELO-B'):
            case = self.store.read(identifier)['case']
            state = self.store.apply('dossier', {**dossier.generate(case['evidence'], 'local'), 'case_id': identifier})
            self.store.apply('decision', {'case_id': identifier, 'actor': 'Revisor', 'reason': 'Investigar', 'review': 'accept', 'outcome': 'qualify', 'dossier_revision': state['case']['dossier']['revision']})
        self.store.apply('action', {'case_id': 'ELO-1042', 'actor': 'Analista', 'title': 'Rever controle', 'owner': 'Gestor', 'due': '2027-01-01'})
        with self.assertRaises(WorkflowError):
            self.store.apply('action/update', {'case_id': 'ELO-B', 'id': 'REC-001', 'actor': 'Gestor', 'status': 'done', 'evidence': 'Documento'})
        self.assertEqual(self.store.read()['actions'][0]['status'], 'open')

    def test_legacy_snapshot_keeps_original_hash_until_audited_write(self):
        # Manufacture a valid original-schema snapshot in an isolated database.
        legacy = initial_state()
        from domain import match_case
        legacy['case'] = match_case(legacy['dataset'])
        legacy['case'].pop('records')
        legacy['case'].pop('rule')
        encoded_state = serialize(legacy)
        event = {'seq': 1, 'at': '2026-11-22T00:00:00Z', 'action': 'Indício detectado', 'actor': 'Regra', 'details': {}, 'previous_hash': '', 'state_hash': hashlib.sha256(encoded_state.encode()).hexdigest()}
        encoded_event = serialize(event)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('UPDATE workflow SET value=? WHERE id=1', (encoded_state,))
            db.execute('INSERT INTO audit VALUES (1,?,?)', (encoded_event, hashlib.sha256(encoded_event.encode()).hexdigest()))
        self.assertTrue(self.store.read()['audit_valid'])
        self.assertNotIn('cases', self.store.export_state())
        self.store.apply('import', self.batch())
        state = self.store.apply('detect', {})
        self.assertEqual(len(state['cases']), 2)
        self.assertTrue(state['audit_valid'])
        self.assertEqual(state['audit'][0]['hash'], hashlib.sha256(encoded_event.encode()).hexdigest())


    def test_stale_impact_cannot_overwrite_changed_shared_level(self):
        state = initial_state()
        transition(state, 'detect', {})
        transition(state, 'dossier', dossier.generate(state['case']['evidence'], 'local'))
        transition(state, 'decision', {'actor': 'Analista', 'reason': 'Analisar vínculo', 'review': 'accept', 'outcome': 'qualify', 'dossier_revision': state['case']['dossier']['revision']})
        state['risk']['level'] = 'Baixa'
        with self.assertRaises(WorkflowError):
            transition(state, 'impact', {'actor': 'Revisor', 'kind': 'risk', 'outcome': 'approved', 'reason': 'Analisado'})
        self.assertEqual(state['risk']['level'], 'Baixa')
        self.assertEqual(state['case']['impacts'][0]['status'], 'pending')

    def test_tampering_imported_dataset_invalidates_hash(self):
        self.store.apply('import', self.batch())
        with closing(sqlite3.connect(self.path)) as db, db:
            state = json.loads(db.execute('SELECT value FROM workflow').fetchone()[0])
            state['dataset']['employees'][-1]['name'] = 'Alteração externa'
            db.execute('UPDATE workflow SET value=?', (serialize(state),))
        self.assertFalse(self.store.read()['audit_valid'])


if __name__ == '__main__':
    unittest.main()
