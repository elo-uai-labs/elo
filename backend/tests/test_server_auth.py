"""HTTP authentication is optional and enforces identity and authorization server-side."""
import json
import base64
import sys
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from access import AccessService, password_record
from domain import Store, WorkflowError
from server import EloServer


class AuthServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.secret = 'synthetic-test-passphrase'
        cls.record = password_record(cls.secret)

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        root = Path(folder.name)
        config = root / 'users.json'
        config.write_text(json.dumps({'version': 1, 'users': [
            {'id': identifier, 'name': identifier, 'roles': roles, 'active': True, 'password': self.record}
            for identifier, roles in [('alice', ['analyst']), ('bob', ['reviewer']), ('worker', ['operator']), ('eve', ['auditor']), ('admin', ['admin'])]]}))
        config.chmod(0o600)
        self.clock = [0]
        self.access = AccessService(config, clock=lambda: self.clock[0], session_ttl=30)
        self.store = Store(root / 'auth.sqlite3')
        self.server = EloServer(('127.0.0.1', 0), self.store, access_service=self.access)
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(lambda: (self.server.shutdown(), self.server.server_close(), thread.join()))

    def request(self, method='GET', path='/api/state', data=None, cookie=None, headers=None):
        connection = HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        try:
            request_headers = {'Content-Type': 'application/json', **(headers or {})}
            if cookie:
                request_headers['Cookie'] = cookie
            connection.request(method, path, json.dumps(data) if data is not None else None, request_headers)
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), json.loads(response.read())
        finally:
            connection.close()

    def login(self, username):
        status, headers, body = self.request('POST', '/api/login', {'username': username, 'password': self.secret})
        self.assertEqual(status, 200)
        self.assertEqual(body['user']['id'], username)
        return headers['Set-Cookie'].split(';')[0]

    def qualified(self):
        cookie = self.login('alice')
        self.assertEqual(self.request('POST', '/api/detect', {'actor': 'admin', 'authentication': {'mode': 'local-auth', 'user_id': 'admin'}}, cookie)[0], 200)
        status, _, state = self.request('POST', '/api/dossier', {'mode': 'local', 'actor': 'admin'}, cookie)
        self.assertEqual(status, 200)
        status, _, state = self.request('POST', '/api/decision', {'actor': 'admin', 'outcome': 'qualify', 'review': 'adjust', 'reason': 'Conferido', 'dossier_revision': state['case']['dossier']['revision'], 'linkage_revision': state['case']['linkage_revision']}, cookie)
        self.assertEqual(status, 200)
        return cookie, state

    def test_session_auth_protection_cookie_logout_expiry(self):
        for path in ('/api/state', '/api/audit/export', '/api/supervision', '/api/laboratory', '/api/insights', '/api/people', '/api/evidence/EVD-0001'):
            self.assertEqual(self.request(path=path)[0], 401)
        status, _, state = self.request(path='/api/session')
        self.assertEqual(state, {'auth_required': True, 'authenticated': False, 'user': None, 'mode': 'local-auth'})
        self.assertEqual(self.request(path='/health')[0], 200)
        status, headers, state = self.request('POST', '/api/login', {'username': 'alice', 'password': self.secret})
        self.assertEqual(status, 200)
        self.assertIn('HttpOnly', headers['Set-Cookie'])
        self.assertIn('SameSite=Strict', headers['Set-Cookie'])
        self.assertIn('Max-Age=30', headers['Set-Cookie'])
        cookie = headers['Set-Cookie'].split(';')[0]
        self.assertEqual(self.request(cookie=cookie)[0], 200)
        self.clock[0] = 31
        self.assertEqual(self.request(cookie=cookie)[0], 401)
        cookie = self.login('alice')
        status, headers, _ = self.request('POST', '/api/logout', {}, cookie)
        self.assertEqual(status, 200)
        self.assertIn('Max-Age=0', headers['Set-Cookie'])
        self.assertEqual(self.request(cookie=cookie)[0], 401)
        self.assertEqual(self.store.read()['audit'], [])

    def test_mutation_actor_cannot_be_spoofed_and_auditor_cannot_write(self):
        cookie, state = self.qualified()
        self.assertEqual([event['actor'] for event in state['audit']], ['alice', 'alice', 'alice'])
        self.assertTrue(all(event['authentication'] == {'mode': 'local-auth', 'user_id': 'alice'} for event in state['audit']))
        self.assertEqual(state['audit'][0]['details']['system_component'], 'Regra de detecção')
        self.assertEqual(state['audit'][1]['details']['system_component'], 'Serviço de síntese')
        self.assertNotIn('actor', state['case']['dossier'])
        auditor = self.login('eve')
        self.assertEqual(self.request('POST', '/api/risk/save', {'actor': 'admin'}, auditor)[0], 403)
        self.assertEqual(len(self.store.read()['audit']), 3)
        self.assertEqual(self.request('POST', '/api/impact', {'actor': 'bob', 'kind': 'risk', 'outcome': 'approved', 'reason': 'Conferido'}, cookie)[0], 403)
        reviewer = self.login('bob')
        self.assertEqual(self.request('POST', '/api/impact', {'kind': 'risk', 'outcome': 'approved', 'reason': 'Revisão independente'}, reviewer)[0], 200)
        self.assertEqual(self.store.read()['audit'][-1]['actor'], 'bob')

    def test_action_owner_and_independent_closure(self):
        analyst, _ = self.qualified()
        payload = {'actor': 'spoof', 'title': 'Plano sintético', 'owner': 'unknown', 'due': '2027-01-01'}
        self.assertEqual(self.request('POST', '/api/action', payload, analyst)[0], 422)
        status, _, state = self.request('POST', '/api/action', {**payload, 'owner': 'worker'}, analyst)
        self.assertEqual(status, 200)
        action = state['actions'][0]
        payload = {'id': action['id'], 'actor': 'worker', 'status': 'closure_requested', 'evidence': 'Ata sintética', 'action_revision': action['revision']}
        self.assertEqual(self.request('POST', '/api/action/update', payload, analyst)[0], 403)
        worker = self.login('worker')
        status, _, state = self.request('POST', '/api/action/update', payload, worker)
        self.assertEqual(status, 200)
        action = state['actions'][0]
        self.assertEqual(action['closure_request']['actor'], 'worker')
        payload = {'id': action['id'], 'actor': 'bob', 'outcome': 'approved', 'reason': 'Conferido', 'action_revision': action['revision']}
        self.assertEqual(self.request('POST', '/api/action/close', payload, worker)[0], 403)
        reviewer = self.login('bob')
        self.assertEqual(self.request('POST', '/api/action/close', payload, reviewer)[0], 200)
        self.assertEqual(self.store.read()['actions'][0]['status'], 'done')

    def test_protected_evidence_and_report_review_workflow(self):
        analyst, state = self.qualified()
        payload = {'case_id': 'ELO-1042', 'actor': 'admin', 'name': 'ata.txt', 'media_type': 'text/plain',
                   'description': 'Fonte sintética', 'synthetic': True, 'content_base64': base64.b64encode(b'Ata sintetica').decode()}
        status, _, state = self.request('POST', '/api/evidence/upload', payload, analyst)
        self.assertEqual(status, 200)
        self.assertEqual(state['attachments'][0]['actor'], 'alice')
        worker = self.login('worker')
        self.assertEqual(self.request('POST', '/api/evidence/upload', payload, worker)[0], 403)
        status, _, state = self.request('POST', '/api/report/create', {'actor': 'admin', 'title': 'Relatório sintético', 'case_ids': ['ELO-1042']}, analyst)
        self.assertEqual(status, 200)
        report = state['reports'][0]
        self.assertEqual(report['creator'], 'alice')
        self.assertEqual(report['status'], 'draft')
        review = {'id': report['id'], 'report_revision': report['revision'], 'actor': 'bob', 'outcome': 'approved', 'reason': 'Fontes conferidas'}
        self.assertEqual(self.request('POST', '/api/report/review', review, analyst)[0], 403)
        reviewer = self.login('bob')
        status, _, state = self.request('POST', '/api/report/review', review, reviewer)
        self.assertEqual(status, 200)
        self.assertEqual(state['reports'][0]['status'], 'approved')
        self.assertEqual(state['reports'][0]['review']['actor'], 'bob')
        self.assertTrue(state['audit_valid'])

    def test_auditor_can_consult_with_canonical_identity_without_business_mutation(self):
        _, before = self.qualified()
        payload = {'actor': 'admin', 'case_id': 'ELO-1042', 'mode': 'local', 'question': 'Qual o risco vigente?'}
        self.assertEqual(self.request('POST', '/api/assistant/query', payload)[0], 401)
        auditor = self.login('eve')
        status, _, state = self.request('POST', '/api/assistant/query', payload, auditor)
        self.assertEqual(status, 200)
        self.assertEqual(state['assistant_queries'][0]['actor'], 'eve')
        self.assertEqual(state['audit'][-1]['authentication'], {'mode': 'local-auth', 'user_id': 'eve'})
        for key in ('cases', 'risks', 'dimensions', 'actions'):
            self.assertEqual(state[key], before[key])

    def test_assistant_rechecks_session_after_generation(self):
        import consultation
        self.qualified()
        auditor = self.login('eve')
        before = self.store.export_state()
        original = consultation.answer
        def expire_during_answer(context):
            result = original(context)
            self.clock[0] = 31
            return result
        with patch('consultation.answer', side_effect=expire_during_answer):
            status, _, _ = self.request('POST', '/api/assistant/query', {'case_id': 'ELO-1042', 'mode': 'local', 'question': 'Qual o risco vigente?'}, auditor)
        self.assertEqual(status, 401)
        self.assertEqual(self.store.export_state(), before)

    def test_scenario_authorization_is_server_side(self):
        auditor = self.login('eve')
        risk = self.store.read()['risk']
        payload = {'actor': 'admin', 'reason': 'Simulação sintética', 'risk_id': risk['id'], 'risk_revision': risk['revision'], 'likelihood': 1, 'impact': 1}
        self.assertEqual(self.request('POST', '/api/scenario/create', payload, auditor)[0], 403)
        self.assertEqual(self.store.read()['scenarios'], [])
        reviewer = self.login('bob')
        status, _, state = self.request('POST', '/api/scenario/create', payload, reviewer)
        self.assertEqual(status, 200)
        self.assertEqual(state['scenarios'][0]['actor'], 'bob')
        self.assertEqual(state['risk'], risk)

    def test_login_origin_and_invalid_config_fail_closed(self):
        self.assertEqual(self.request('POST', '/api/login', {'username': 'alice', 'password': self.secret}, headers={'Origin': 'https://evil.example'})[0], 403)
        self.assertEqual(self.request('POST', '/api/login', {'username': 'alice', 'password': 'wrong'})[0], 401)
        with patch.dict('os.environ', {'ELO_AUTH_USERS_FILE': '/missing/synthetic-config.json'}):
            with self.assertRaises(OSError):
                EloServer(('127.0.0.1', 0), self.store)

    def test_authorization_callback_is_transactional_and_rolls_back(self):
        visited = []
        def deny(snapshot):
            visited.append(snapshot)
            raise WorkflowError('Not allowed', 403)
        before = self.store.export_state()
        with self.assertRaises(WorkflowError):
            self.store.apply('detect', {}, authorize=deny)
        self.assertEqual(len(visited), 1)
        self.assertEqual(self.store.export_state(), before)


if __name__ == '__main__':
    unittest.main()
