"""HTTP import trust boundaries; synthetic accounts and temporary databases only."""
import base64
import json
from http.client import HTTPConnection
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from access import AccessService, password_record
from domain import Store
from server import EloServer
import tabular_import


class TabularHttpTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.password = 'temporary-synthetic-password'
        cls.password_hash = password_record(cls.password)

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        accounts = root / 'accounts.json'
        accounts.write_text(json.dumps({'version': 1, 'users': [
            {'id': role, 'name': role, 'roles': [role], 'active': True, 'password': self.password_hash}
            for role in ('analyst', 'operator', 'auditor', 'admin')]}))
        accounts.chmod(0o600)
        self.clock = [0]
        self.store = Store(root / 'test.sqlite3')
        self.server = EloServer(('127.0.0.1', 0), self.store,
            access_service=AccessService(accounts, clock=lambda: self.clock[0], session_ttl=30))
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(lambda: (self.server.shutdown(), self.server.server_close(), thread.join()))

    def request(self, path, data, cookie=None):
        conn = HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        try:
            conn.request('POST', path, json.dumps(data),
                {'Content-Type': 'application/json', **({'Cookie': cookie} if cookie else {})})
            response = conn.getresponse()
            return response.status, dict(response.getheaders()), json.loads(response.read())
        finally:
            conn.close()

    def login(self, role):
        status, headers, _ = self.request('/api/login', {'username': role, 'password': self.password})
        self.assertEqual(status, 200)
        return headers['Set-Cookie'].split(';')[0]

    def batch(self, text=None, **changes):
        text = text if text is not None else 'id,name,role,contact_code\nEMP-HTTP,Pessoa fictícia,Aprovador,SYN-HTTP\n'
        return {'filename': 'pessoas.csv', 'table': 'employees', 'synthetic': True,
                'actor': 'forged-admin', 'authentication': {'mode': 'local-auth', 'user_id': 'admin'},
                'content_base64': base64.b64encode(text.encode()).decode(), **changes}

    def test_authentication_and_roles_restrict_preview_and_import(self):
        before = self.store.read()
        for endpoint in ('/api/import/preview', '/api/import/file'):
            self.assertEqual(self.request(endpoint, self.batch())[0], 401)
        for role in ('operator', 'auditor'):
            cookie = self.login(role)
            for endpoint in ('/api/import/preview', '/api/import/file'):
                self.assertEqual(self.request(endpoint, self.batch(), cookie)[0], 403)
        self.assertEqual(self.store.read(), before)
        admin = self.login('admin')
        self.assertEqual(self.request('/api/import/preview', self.batch(), admin)[0], 200)

    def test_preview_has_no_business_mutation_and_import_identity_is_canonical(self):
        cookie = self.login('analyst')
        before = self.store.read()
        status, _, result = self.request('/api/import/preview', self.batch(), cookie)
        self.assertEqual(status, 200)
        self.assertTrue(result['ready'])
        self.assertEqual(result['counts']['records'], 1)
        self.assertEqual(self.store.read(), before)
        status, _, state = self.request('/api/import/file', self.batch(), cookie)
        self.assertEqual(status, 200)
        self.assertEqual(state['audit'][-1]['actor'], 'analyst')
        self.assertEqual(state['audit'][-1]['authentication'], {'mode': 'local-auth', 'user_id': 'analyst'})
        self.assertEqual(state['audit'][-1]['details']['record_ids']['employees'], ['EMP-HTTP'])
        self.assertTrue(state['audit_valid'])

    def test_server_ignores_forged_dataset_and_rejects_duplicate_confirmation(self):
        cookie = self.login('analyst')
        body = self.batch(dataset={'employees': [{'id': 'EMP-FORGED'}], 'suppliers': [], 'contracts': []}, ready=True, errors=[])
        status, _, state = self.request('/api/import/file', body, cookie)
        self.assertEqual(status, 200)
        ids = [row['id'] for row in state['dataset']['employees']]
        self.assertIn('EMP-HTTP', ids)
        self.assertNotIn('EMP-FORGED', ids)
        before = self.store.read()
        status, _, result = self.request('/api/import/preview', body, cookie)
        self.assertEqual(status, 200)
        self.assertFalse(result['ready'])
        self.assertEqual(result['errors'][0]['row'], 2)
        self.assertEqual(self.request('/api/import/file', body, cookie)[0], 409)
        self.assertEqual(self.store.read(), before)

    def test_invalid_reference_cannot_be_bypassed_by_client_preview(self):
        cookie = self.login('analyst')
        before = self.store.read()
        body = self.batch('id,supplier_id,approver_id,title\nCTR-HTTP,FOR-MISSING,EMP-MISSING,Contrato fictício\n',
            table='contracts', ready=True, errors=[], dataset={
                'employees': [{'id': 'EMP-MISSING', 'name': 'Fake', 'role': 'A', 'contact_code': 'S'}],
                'suppliers': [{'id': 'FOR-MISSING', 'name': 'Fake', 'contact_code': 'S'}],
                'contracts': [{'id': 'CTR-HTTP', 'supplier_id': 'FOR-MISSING', 'approver_id': 'EMP-MISSING', 'title': 'Fake'}]})
        status, _, result = self.request('/api/import/preview', body, cookie)
        self.assertEqual(status, 200)
        self.assertEqual({e['field'] for e in result['errors']}, {'supplier_id', 'approver_id'})
        self.assertEqual(self.request('/api/import/file', body, cookie)[0], 409)
        self.assertEqual(self.store.read(), before)

    def test_format_size_and_synthetic_confirmation_errors_do_not_mutate(self):
        cookie = self.login('analyst')
        before = self.store.read()
        cases = [
            (self.batch(filename='data.exe'), 422),
            (self.batch(content_base64='not-base64!'), 422),
            (self.batch(content_base64=base64.b64encode(b'a' * (256 * 1024 + 1)).decode()), 422),
            (self.batch(padding='a' * 524288), 413),
            (self.batch(synthetic=False), 409),
        ]
        for body, expected in cases:
            for endpoint in ('/api/import/preview', '/api/import/file'):
                with self.subTest(endpoint=endpoint, expected=expected):
                    status, _, result = self.request(endpoint, body, cookie)
                    self.assertEqual(status, expected, result)
                    self.assertIn('error', result)
        self.assertEqual(self.store.read(), before)

    def test_session_revalidated_inside_import_transaction(self):
        cookie = self.login('analyst')
        before = self.store.read()
        original = tabular_import.preview
        def expire_after_preview(*args, **kwargs):
            result = original(*args, **kwargs)
            self.clock[0] = 31
            return result
        with patch('tabular_import.preview', side_effect=expire_after_preview):
            status, _, _ = self.request('/api/import/file', self.batch(), cookie)
        self.assertEqual(status, 401)
        self.assertEqual(self.store.read(), before)


if __name__ == '__main__':
    unittest.main()
