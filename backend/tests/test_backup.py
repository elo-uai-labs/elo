import base64
import os
import sqlite3
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import consultation
import dossier
from access_audit import AccessAudit
from backup import verified_copy
from domain import Store, WorkflowError


class BackupTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.source = self.root / 'source.sqlite3'
        self.destination = self.root / 'copy.sqlite3'
        self.store = Store(self.source)
        self.store.apply('detect', {})
        self.store.apply('evidence/upload', {'case_id': 'ELO-1042', 'actor': 'Teste',
            'name': 'teste.txt', 'media_type': 'text/plain', 'description': 'Sintético',
            'synthetic': True, 'content_base64': base64.b64encode(b'evidence').decode()})

    def test_backup_restore_exact_snapshot_source_unchanged_private(self):
        before, mtime = self.source.read_bytes(), self.source.stat().st_mtime_ns
        expected = self.store.export_state(include_files=True)
        result = verified_copy(self.source, self.destination)
        self.assertEqual(result, {'status': 'verified', 'audit_events': 2, 'attachments': 1})
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(self.source.stat().st_mtime_ns, mtime)
        self.assertEqual(Store(self.destination).export_state(include_files=True), expected)
        self.assertEqual(self.destination.stat().st_mode & 0o777, 0o600)
        restored = self.root / 'restore.sqlite3'
        verified_copy(self.destination, restored)
        self.assertEqual(Store(restored).export_state(include_files=True), expected)
        self.assertEqual(list(self.root.glob('.elo-backup-*')), [])

    def test_reports_and_queries_preserved_as_complete_audited_snapshot(self):
        state = self.store.read()
        state = self.store.apply('dossier', dossier.generate(state['case']['evidence'], 'local'))
        self.store.apply('decision', {'actor': 'Analista', 'review': 'accept', 'outcome': 'qualify',
            'reason': 'Revisão sintética', 'dossier_revision': state['case']['dossier']['revision']})
        self.store.apply('report/create', {'actor': 'Analista', 'title': 'Relatório sintético', 'case_ids': ['ELO-1042']})
        context = consultation.prepare(self.store.read(), {'case_id': 'ELO-1042', 'question': 'Qual risco?', 'mode': 'local'})
        self.store.apply('assistant/record', {'actor': 'Auditor', 'answer': consultation.answer(context)})
        expected = self.store.export_state(include_files=True)
        self.assertEqual(len(expected['reports']), 1)
        self.assertEqual(len(expected['assistant_queries']), 1)
        result = verified_copy(self.source, self.destination)
        self.assertEqual(result['audit_events'], len(expected['audit']))
        restored = self.root / 'restored-complete.sqlite3'
        verified_copy(self.destination, restored)
        self.assertEqual(Store(restored).export_state(include_files=True), expected)

    def test_missing_empty_foreign_symlink_rejected_without_destination(self):
        empty = self.root / 'empty'; empty.touch()
        foreign = self.root / 'foreign'
        with closing(sqlite3.connect(foreign)) as db:
            db.execute('CREATE TABLE unrelated (id)')
        link = self.root / 'link'; link.symlink_to(self.source)
        for path in (self.root / 'missing', empty, foreign, link):
            with self.assertRaises((ValueError, OSError)):
                verified_copy(path, self.destination)
            self.assertFalse(self.destination.exists())
        self.assertFalse((self.root / 'missing').exists())

    def test_audit_and_blob_tamper_rejected(self):
        for kind in ('audit', 'blob'):
            with self.subTest(kind=kind):
                corrupt = self.root / (kind + '.sqlite3')
                verified_copy(self.source, corrupt)
                with closing(sqlite3.connect(corrupt)) as db, db:
                    if kind == 'audit':
                        db.execute('DROP TRIGGER audit_no_update')
                        db.execute("UPDATE audit SET hash='tampered' WHERE seq=1")
                    else:
                        db.execute('DROP TRIGGER evidence_no_update')
                        db.execute("UPDATE evidence_files SET content=x'00'")
                before = corrupt.read_bytes()
                with self.assertRaises((WorkflowError, ValueError)):
                    verified_copy(corrupt, self.destination)
                self.assertFalse(self.destination.exists())
                self.assertEqual(corrupt.read_bytes(), before)
                self.assertEqual(list(self.root.glob('.elo-backup-*')), [])

    def test_publish_race_cannot_overwrite(self):
        real_link = os.link
        def competing_publish(source, destination):
            Path(destination).write_bytes(b'other writer')
            real_link(source, destination)
        with patch('backup.os.link', side_effect=competing_publish):
            with self.assertRaises(FileExistsError):
                verified_copy(self.source, self.destination)
        self.assertEqual(self.destination.read_bytes(), b'other writer')
        self.assertEqual(list(self.root.glob('.elo-backup-*')), [])
        with self.assertRaises(FileExistsError):
            verified_copy(self.source, self.source)

    def test_access_ledger_preserved_and_corruption_blocks_copy(self):
        ledger = AccessAudit(self.source)
        ledger.append(actor='auditor', mode='local-auth', event='export', target='/api/audit/export', outcome='success', ip='127.0.0.1')
        expected = ledger.export()
        verified_copy(self.source, self.destination)
        self.assertEqual(AccessAudit(self.destination).export(), expected)
        restored = self.root / 'access-restored.sqlite3'
        verified_copy(self.destination, restored)
        self.assertEqual(AccessAudit(restored).export(), expected)
        with closing(sqlite3.connect(self.source)) as db, db:
            db.execute('DROP TRIGGER access_audit_no_update')
            db.execute("UPDATE access_audit SET hash='corrupt'")
        invalid = self.root / 'invalid.sqlite3'
        with self.assertRaises(ValueError):
            verified_copy(self.source, invalid)
        self.assertFalse(invalid.exists())

    def test_concurrent_source_writer_consistent_backup(self):
        def writer():
            for index in range(8):
                self.store.apply('evidence/upload', {'case_id': 'ELO-1042', 'actor': 'Teste',
                    'name': f'{index}.txt', 'media_type': 'text/plain', 'description': 'Sintético',
                    'synthetic': True, 'content_base64': base64.b64encode(str(index).encode()).decode()})
        with ThreadPoolExecutor(max_workers=2) as pool:
            future = pool.submit(writer)
            verified_copy(self.source, self.destination)
            future.result()
        snapshot = Store(self.destination).export_state(include_files=True)
        self.assertTrue(snapshot['audit_valid'])
        self.assertEqual(len(snapshot['attachment_files']) + 1, len(snapshot['audit']))
        self.assertEqual(len(self.store.read()['audit']), 10)


if __name__ == '__main__':
    unittest.main()
