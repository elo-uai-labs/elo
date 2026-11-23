import base64
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dossier
from domain import Store, WorkflowError


class EvidenceStoreTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / 'evidence.sqlite3'
        self.store = Store(self.path)
        self.store.apply('detect', {})
        self.payload = {'case_id': 'ELO-1042', 'actor': 'Analista', 'name': 'ata.txt', 'media_type': 'text/plain',
                        'content_base64': base64.b64encode(b'Ata sintetica').decode(), 'description': 'Fonte de execução sintética', 'synthetic': True}

    def qualify_and_plan(self):
        state = self.store.read()
        state = self.store.apply('dossier', dossier.generate(state['case']['evidence'], 'local'))
        self.store.apply('decision', {'actor': 'Analista', 'review': 'accept', 'outcome': 'qualify', 'reason': 'Investigar', 'dossier_revision': state['case']['dossier']['revision']})
        return self.store.apply('action', {'actor': 'Analista', 'title': 'Rever controle', 'owner': 'Executor', 'due': '2027-01-01'})['actions'][0]

    def test_upload_download_restart_and_export_atomic(self):
        state = self.store.apply('evidence/upload', self.payload)
        metadata = state['attachments'][0]
        self.assertEqual(metadata['id'], 'EVD-0001')
        self.assertNotIn('content_base64', metadata)
        self.assertTrue(state['audit_valid'])
        metadata, content = Store(self.path).evidence_file('EVD-0001')
        self.assertEqual(content, b'Ata sintetica')
        export = self.store.export_state(include_files=True)
        self.assertEqual(export['attachment_files'][0]['content_base64'], self.payload['content_base64'])
        self.assertNotIn('attachment_files', self.store.read())
        with closing(sqlite3.connect(self.path)) as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE evidence_files SET content = x'00'")
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute('DELETE FROM evidence_files')

    def test_invalid_target_rolls_back_bytes_and_audit(self):
        before = self.store.export_state(include_files=True)
        for changes in ({'case_id': 'ELO-MISSING'}, {'action_id': 'REC-999'}, {'synthetic': False}):
            with self.assertRaises(WorkflowError):
                self.store.apply('evidence/upload', {**self.payload, **changes})
            self.assertEqual(self.store.export_state(include_files=True), before)
        with patch('evidence.MAX_TOTAL_BYTES', 1):
            with self.assertRaises(WorkflowError):
                self.store.apply('evidence/upload', self.payload)
        with patch('evidence.MAX_FILES', 0):
            with self.assertRaises(WorkflowError):
                self.store.apply('evidence/upload', self.payload)
        self.assertEqual(self.store.export_state(include_files=True), before)

    def test_attachment_can_support_closure_and_is_frozen_during_review(self):
        action = self.qualify_and_plan()
        state = self.store.apply('evidence/upload', {**self.payload, 'action_id': action['id']})
        state = self.store.apply('action/update', {'actor': 'Executor', 'id': action['id'], 'action_revision': state['actions'][0]['revision'], 'status': 'closure_requested', 'evidence': ''})
        self.assertEqual(state['actions'][0]['closure_request']['attachment_ids'], ['EVD-0001'])
        with self.assertRaises(WorkflowError):
            self.store.apply('evidence/upload', {**self.payload, 'action_id': action['id']})
        self.assertEqual(len(self.store.export_state(include_files=True)['attachment_files']), 1)
        state = self.store.apply('action/close', {'actor': 'Revisor', 'id': action['id'], 'action_revision': state['actions'][0]['revision'], 'outcome': 'approved', 'reason': 'Arquivo conferido'})
        self.assertEqual(state['actions'][0]['status'], 'done')
        self.assertTrue(state['audit_valid'])

    def test_file_tampering_and_unreferenced_rows_detected(self):
        self.store.apply('evidence/upload', self.payload)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('DROP TRIGGER evidence_no_update')
            db.execute("UPDATE evidence_files SET content = x'00'")
        self.assertFalse(self.store.read()['audit_valid'])
        with self.assertRaises(WorkflowError):
            self.store.evidence_file('EVD-0001')
        with self.assertRaises(WorkflowError):
            self.store.apply('evidence/upload', self.payload)

    def test_unreferenced_blob_invalidates_initial_state(self):
        path = self.path.with_name('empty.sqlite3')
        other = Store(path)
        with closing(sqlite3.connect(path)) as db, db:
            db.execute('INSERT INTO evidence_files VALUES (?, ?)', ('EVD-0001', b'orphan'))
        self.assertFalse(other.read()['audit_valid'])


if __name__ == '__main__':
    unittest.main()
