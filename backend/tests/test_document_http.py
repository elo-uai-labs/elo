"""Independent security regression checks; only temporary stores/accounts."""
import base64
import json
import sqlite3
import sys
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from access import AccessService, provision
from domain import Store
from server import EloServer


class DocumentHttpTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.store = Store(self.root / 'test.db')
        self.store.apply('detect', {})
        self.store.apply('evidence/upload', {'actor': 'Demo', 'case_id': 'ELO-1042', 'synthetic': True,
            'name': 'literal.txt', 'media_type': 'text/plain', 'description': 'Sintético',
            'content_base64': base64.b64encode(b'Literal CTR-1042 FOR-UNKNOWN.').decode()})
        self.server = EloServer(('127.0.0.1', 0), self.store, access_service=None)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.shutdown)

    def shutdown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join()

    def request(self, path, data=None, cookie=None):
        conn = HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        try:
            conn.request('POST' if data is not None else 'GET', path,
                json.dumps(data) if data is not None else None,
                {'Content-Type': 'application/json', **({'Cookie': cookie} if cookie else {})})
            response = conn.getresponse()
            return response.status, dict(response.getheaders()), json.loads(response.read())
        finally:
            conn.close()

    def test_forged_analysis_ignored_private_endpoint_closed_and_review_cas(self):
        before = self.store.read()
        self.assertEqual(self.request('/api/document/record', {'actor': 'Demo', 'analysis': {}})[0], 404)
        self.assertEqual(self.store.read(), before)
        status, _, state = self.request('/api/evidence/analyze', {'actor': 'Demo', 'attachment_id': 'EVD-0001',
            'analysis': {'text': 'FORGED', 'status': 'accepted'}, 'mode': 'literal'})
        self.assertEqual(status, 200)
        entry = state['document_analyses'][0]
        self.assertEqual(entry['text'], 'Literal CTR-1042 FOR-UNKNOWN.')
        self.assertEqual(entry['status'], 'pending')
        self.assertEqual(entry['unknown_ids'], ['FOR-UNKNOWN'])
        self.assertEqual(entry['record_ids'], ['CTR-1042'])
        review = {'actor': 'Reviewer', 'analysis_id': entry['id'], 'revision': entry['revision'],
                  'confirmed': True, 'outcome': 'accepted', 'reason': 'Texto conferido.'}
        self.assertEqual(self.request('/api/evidence/review', {**review, 'revision': '0' * 64})[0], 409)
        self.assertEqual(self.request('/api/evidence/review', review)[0], 200)
        self.assertEqual(self.request('/api/evidence/review', review)[0], 409)
        self.assertTrue(self.store.read()['audit_valid'])

    def test_roles_identity_and_access_export_separation(self):
        password = 'temporary-secret-12345'
        config = self.root / 'accounts.json'
        for role in ('analyst', 'reviewer', 'operator', 'auditor'):
            provision(config, role, role, [role], password)
        self.server.access = AccessService(config)
        self.assertEqual(self.request('/api/evidence/analyze', {})[0], 401)
        cookies = {}
        for role in ('analyst', 'reviewer', 'operator', 'auditor'):
            status, headers, _ = self.request('/api/login', {'username': role, 'password': password})
            self.assertEqual(status, 200)
            cookies[role] = headers['Set-Cookie'].split(';')[0]
        payload = {'actor': 'forged', 'attachment_id': 'EVD-0001'}
        for role in ('operator', 'auditor'):
            self.assertEqual(self.request('/api/evidence/analyze', payload, cookies[role])[0], 403)
            self.assertEqual(self.request('/api/evidence/review', {'actor': 'forged'}, cookies[role])[0], 403)
        status, _, state = self.request('/api/evidence/analyze', payload, cookies['analyst'])
        self.assertEqual(status, 200)
        self.assertEqual(state['document_analyses'][0]['actor'], 'analyst')
        self.assertEqual(state['audit'][-1]['authentication']['user_id'], 'analyst')
        self.assertEqual(self.request('/api/access-audit/export', cookie=cookies['analyst'])[0], 403)
        self.assertEqual(self.request('/api/access-audit/export', cookie=cookies['auditor'])[0], 200)

    def test_receipt_failure_blocks_response_but_business_commit_remains_audited(self):
        with patch.object(self.server.access_audit, 'append', side_effect=sqlite3.OperationalError('offline')):
            status, _, response = self.request('/api/evidence/analyze', {'actor': 'Demo', 'attachment_id': 'EVD-0001'})
        self.assertEqual(status, 503)
        self.assertIn('confira o estado', response['error'])
        state = self.store.read()
        self.assertEqual(len(state['document_analyses']), 1)
        self.assertTrue(state['audit_valid'])
        self.assertEqual(self.request('/api/evidence/analyze', {'actor': 'Demo', 'attachment_id': 'EVD-0001'})[0], 409)
        before = self.store.read()
        with patch.object(self.server.access_audit, 'export', side_effect=ValueError('corrupt')):
            self.assertEqual(self.request('/api/evidence/analyze', {'actor': 'Demo', 'attachment_id': 'EVD-0001'})[0], 503)
        self.assertEqual(self.store.read(), before)

    def test_structural_ledger_errors_fail_closed(self):
        before = self.store.read()
        for failure in (TypeError('shape'), KeyError('missing'), OverflowError('bounds')):
            with self.subTest(error=type(failure).__name__):
                with patch.object(self.server.access_audit, 'export', side_effect=failure):
                    self.assertEqual(self.request('/api/evidence/analyze', {'actor': 'Demo', 'attachment_id': 'EVD-0001'})[0], 503)
                    self.assertEqual(self.request('/api/access-audit/export')[0], 503)
                with patch.object(self.server.access_audit, 'append', side_effect=failure):
                    status, _, response = self.request('/api/state')
                    self.assertEqual(status, 503)
                    self.assertNotIn('dataset', response)
        self.assertEqual(self.store.read(), before)
