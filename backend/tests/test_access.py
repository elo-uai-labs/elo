import copy
import json
import os
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from access import AccessService, ITERATIONS, password_record, provision, validate_config
from domain import WorkflowError


class AccessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.password = 'synthetic-test-password-only'
        cls.record = password_record(cls.password)

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / 'users.json'
        self.config = {'version': 1, 'users': [
            {'id': role, 'name': role.title(), 'roles': [role], 'active': True, 'password': copy.deepcopy(self.record)}
            for role in ('admin', 'analyst', 'reviewer', 'operator', 'auditor')]}
        self.path.write_text(json.dumps(self.config))
        self.path.chmod(0o600)
        self.now = 1000
        self.service = AccessService(self.path, clock=lambda: self.now, session_ttl=60)

    def user(self, role):
        return next(user for user in self.service.people() if user['id'] == role)

    def assert_status(self, status, call):
        with self.assertRaises(WorkflowError) as context:
            call()
        self.assertEqual(context.exception.status, status)

    def test_consultation_readers_and_private_record(self):
        for role in ('admin', 'analyst', 'reviewer', 'operator', 'auditor'):
            self.service.authorize(self.user(role), 'assistant/query', {}, {})
            self.assert_status(403, lambda: self.service.authorize(self.user(role), 'assistant/record', {}, {}))

    def test_password_parameters_and_fail_closed_config(self):
        self.assertEqual(self.record['iterations'], ITERATIONS)
        self.assertEqual(ITERATIONS, 600_000)
        self.assertNotIn(self.password, json.dumps(self.config))
        another = password_record(self.password)
        self.assertNotEqual(self.record['salt'], another['salt'])
        for mutate in (
            lambda c: c.update(version=2),
            lambda c: c['users'][0].update(id='ADMIN'),
            lambda c: c['users'][0].update(roles=['unknown']),
            lambda c: c['users'][0]['password'].update(iterations=1),
            lambda c: c['users'][0]['password'].update(salt='AA=='),
        ):
            config = copy.deepcopy(self.config)
            mutate(config)
            with self.assertRaises(ValueError):
                validate_config(config)
        self.path.chmod(0o644)
        with self.assertRaises(ValueError):
            AccessService(self.path)
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(AccessService.from_environment())

    def test_login_expiration_logout_and_secret_free_people(self):
        token, user = self.service.login('analyst', self.password)
        self.assertEqual(set(user), {'id', 'name', 'roles'})
        self.assertEqual(self.service.session(token), user)
        self.assertNotIn(token, self.service._sessions)
        self.now += 60
        self.assertIsNone(self.service.session(token))
        token, _ = self.service.login('analyst', self.password)
        self.service.logout(token)
        self.assertIsNone(self.service.session(token))
        self.assertIsNone(self.service.session('untrusted'))
        for person in self.service.people():
            self.assertEqual(set(person), {'id', 'name', 'roles'})

    def test_rate_limit_under_concurrent_failures_and_window(self):
        def attempt(_):
            try:
                self.service.login('analyst', 'wrong')
            except WorkflowError as error:
                return error.status
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(attempt, range(8)))
        self.assertEqual(results.count(401), 5)
        self.assertEqual(results.count(429), 3)
        self.assert_status(429, lambda: self.service.login('analyst', self.password))
        self.now += 60
        self.assertEqual(self.service.login('analyst', self.password)[1]['id'], 'analyst')

    def test_disabled_account_and_unknown_are_rejected(self):
        self.config['users'][0]['active'] = False
        self.path.write_text(json.dumps(self.config))
        service = AccessService(self.path)
        for username in ('admin', 'missing'):
            self.assert_status(401, lambda: service.login(username, self.password))
        self.assertNotIn('admin', [p['id'] for p in service.people()])
        self.assert_status(422, lambda: service.validate_owner('admin'))

    def test_limits_bound_sessions_and_failure_keys_without_eviction(self):
        with patch('access.MAX_SESSIONS', 2):
            first, _ = self.service.login('analyst', self.password)
            second, _ = self.service.login('operator', self.password)
            self.assertNotEqual(first, second)
            self.assert_status(429, lambda: self.service.login('reviewer', self.password))
            self.assertEqual(self.service.session(first)['id'], 'analyst')
            self.service.logout(second)
            self.service.login('reviewer', self.password)
        with patch('access.MAX_FAILURE_KEYS', 2):
            self.assert_status(401, lambda: self.service.login('missing-a', 'wrong'))
            self.assert_status(401, lambda: self.service.login('missing-b', 'wrong'))
            self.assert_status(429, lambda: self.service.login('missing-c', 'wrong'))
            self.assertEqual(len(self.service._failures), 2)
            self.now += 60
            self.assert_status(401, lambda: self.service.login('missing-c', 'wrong'))

    def test_role_matrix_and_assignment_enforced(self):
        for role in ('admin', 'analyst', 'reviewer', 'operator', 'auditor'):
            self.service.authorize(self.user(role), 'read')
        self.service.authorize(self.user('analyst'), 'detect')
        self.service.authorize(self.user('reviewer'), 'risk/save')
        self.service.authorize(self.user('admin'), 'risk/save')
        for role, command in (('auditor', 'detect'), ('operator', 'decision'), ('analyst', 'impact'), ('reviewer', 'import')):
            self.assert_status(403, lambda: self.service.authorize(self.user(role), command))
        action = {'id': 'REC-001', 'owner': 'operator', 'closure_request': {'actor': 'admin'}}
        state = {'actions': [action]}
        self.service.authorize(self.user('operator'), 'action/update', state, {'id': 'REC-001'})
        self.assert_status(403, lambda: self.service.authorize(self.user('admin'), 'action/update', state, {'id': 'REC-001'}))
        self.assert_status(403, lambda: self.service.authorize(self.user('admin'), 'action/close', state, {'id': 'REC-001'}))
        self.service.authorize(self.user('reviewer'), 'action/close', state, {'id': 'REC-001'})
        self.assert_status(422, lambda: self.service.authorize(self.user('analyst'), 'action', data={'owner': 'auditor'}))
        self.service.authorize(self.user('analyst'), 'action', data={'owner': 'operator'})
        # Client-provided roles do not escalate the stored identity.
        self.assert_status(403, lambda: self.service.authorize({'id': 'auditor', 'roles': ['admin']}, 'detect'))

    def test_provision_creates_private_file_and_refuses_duplicate(self):
        path = self.path.parent / 'new-users.json'
        provision(path, 'new.operator', 'Pessoa sintética', ['operator'], self.password)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(AccessService(path).people()[0]['id'], 'new.operator')
        before = path.read_bytes()
        with self.assertRaises(ValueError):
            provision(path, 'new.operator', 'Outro', ['admin'], self.password)
        self.assertEqual(path.read_bytes(), before)

    def test_impact_requires_distinct_reviewer_even_for_admin(self):
        state = {'cases': [
            {'id': 'ELO-A', 'decision': {'actor': 'admin'}},
            {'id': 'ELO-B', 'decision': {'actor': 'reviewer'}},
        ]}
        self.assert_status(403, lambda: self.service.authorize(self.user('analyst'), 'impact', state, {'case_id': 'ELO-A'}))
        self.assert_status(403, lambda: self.service.authorize(self.user('admin'), 'impact', state, {'case_id': 'ELO-A'}))
        self.assert_status(403, lambda: self.service.authorize(self.user('admin'), 'impact', state, {}))
        self.assert_status(403, lambda: self.service.authorize(self.user('reviewer'), 'impact', state, {'case_id': 'ELO-B'}))
        self.service.authorize(self.user('reviewer'), 'impact', state, {'case_id': 'ELO-A'})
        self.service.authorize(self.user('admin'), 'impact', state, {'case_id': 'ELO-B'})
        self.assert_status(403, lambda: self.service.authorize(self.user('reviewer'), 'impact', state, {'case_id': 'missing'}))

    def test_evidence_permissions_assignment_case_and_status(self):
        action = {'id': 'REC-001', 'case_id': 'ELO-A', 'owner': 'operator', 'status': 'in_progress'}
        state = {'actions': [action]}
        payload = {'case_id': 'ELO-A', 'action_id': 'REC-001'}
        for role in ('analyst', 'reviewer', 'admin'):
            self.service.authorize(self.user(role), 'evidence/upload', state, {'case_id': 'ELO-A'})
        self.service.authorize(self.user('operator'), 'evidence/upload', state, payload)
        for role in ('operator', 'auditor'):
            self.assert_status(403, lambda: self.service.authorize(self.user(role), 'evidence/upload', state, {'case_id': 'ELO-A'}))
        for role in ('analyst', 'reviewer', 'admin', 'auditor'):
            self.assert_status(403, lambda: self.service.authorize(self.user(role), 'evidence/upload', state, payload))
        self.assert_status(403, lambda: self.service.authorize(self.user('operator'), 'evidence/upload', state, {**payload, 'case_id': 'ELO-B'}))
        for status in ('closure_requested', 'done'):
            action['status'] = status
            self.assert_status(403, lambda: self.service.authorize(self.user('operator'), 'evidence/upload', state, payload))
        self.service.authorize(self.user('auditor'), 'evidence/download')

    def test_report_creation_and_independent_review(self):
        state = {'reports': [{'id': 'RPT-001', 'creator': 'admin'}]}
        for role in ('analyst', 'admin'):
            self.service.authorize(self.user(role), 'report/create', state, {})
        for role in ('reviewer', 'operator', 'auditor'):
            self.assert_status(403, lambda: self.service.authorize(self.user(role), 'report/create', state, {}))
        self.assert_status(403, lambda: self.service.authorize(self.user('admin'), 'report/review', state, {'id': 'RPT-001'}))
        self.assert_status(403, lambda: self.service.authorize(self.user('analyst'), 'report/review', state, {'id': 'RPT-001'}))
        self.service.authorize(self.user('reviewer'), 'report/review', state, {'id': 'RPT-001'})
        state['reports'][0]['creator'] = 'analyst'
        self.service.authorize(self.user('admin'), 'report/review', state, {'id': 'RPT-001'})

    def test_scenarios_require_analytical_or_review_role(self):
        for role in ('analyst', 'reviewer', 'admin'):
            self.service.authorize(self.user(role), 'scenario/create')
        for role in ('operator', 'auditor'):
            self.assert_status(403, lambda: self.service.authorize(self.user(role), 'scenario/create'))


if __name__ == '__main__':
    unittest.main()
