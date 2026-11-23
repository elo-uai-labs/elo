"""Independent adversarial regressions for file-preview and extraction boundaries."""
import base64
import json
import sys
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from domain import Store, WorkflowError
from server import EloServer


class DiagnosticSecurityTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.store = Store(Path(folder.name) / 'security.sqlite3')
        self.store.apply('detect', {})
        self.store.apply('evidence/upload', {'actor': 'Demo', 'case_id': 'ELO-1042', 'synthetic': True,
            'name': 'literal.txt', 'media_type': 'text/plain', 'description': 'Sintético',
            'content_base64': base64.b64encode(b'Literal CTR-1042.').decode()})
        self.server = EloServer(('127.0.0.1', 0), self.store, access_service=None)
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(lambda: (self.server.shutdown(), self.server.server_close(), thread.join()))

    def post(self, path, data):
        connection = HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        try:
            connection.request('POST', path, json.dumps(data), {'Content-Type': 'application/json'})
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def test_unhashable_table_types_are_rejected_and_audited(self):
        before = self.store.read()
        for value in ([], {}, ['contracts']):
            for endpoint in ('/api/import/preview', '/api/import/file'):
                with self.subTest(value=value, endpoint=endpoint):
                    status, body = self.post(endpoint, {'table': value, 'synthetic': True})
                    self.assertEqual(status, 422)
                    self.assertIn('error', body)
        self.assertEqual(self.store.read(), before)
        events = self.server.access_audit.export()['events']
        self.assertEqual(len(events), 6)
        self.assertTrue(all(event['outcome'] == 'error' for event in events))

    def test_busy_extractor_does_not_spawn_or_mutate(self):
        before = self.store.read()
        self.server.document_lock.acquire()
        try:
            with patch('document_analysis.extract') as extract:
                status, body = self.post('/api/evidence/analyze', {'actor': 'Demo', 'attachment_id': 'EVD-0001'})
                self.assertEqual(status, 409)
                self.assertIn('extração em andamento', body['error'])
                extract.assert_not_called()
        finally:
            self.server.document_lock.release()
        self.assertEqual(self.store.read(), before)

    def test_extractor_failure_releases_lock_and_retry_succeeds(self):
        before = self.store.read()
        with patch('document_analysis.extract', side_effect=WorkflowError('Extração inconclusiva.', 409)):
            status, _ = self.post('/api/evidence/analyze', {'actor': 'Demo', 'attachment_id': 'EVD-0001'})
            self.assertEqual(status, 409)
        self.assertFalse(self.server.document_lock.locked())
        self.assertEqual(self.store.read(), before)
        status, result = self.post('/api/evidence/analyze', {'actor': 'Demo', 'attachment_id': 'EVD-0001'})
        self.assertEqual(status, 200)
        self.assertEqual(result['document_analyses'][0]['text'], 'Literal CTR-1042.')
        self.assertFalse(self.server.document_lock.locked())
        self.assertTrue(result['audit_valid'])


if __name__ == '__main__':
    unittest.main()
