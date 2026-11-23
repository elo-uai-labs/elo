"""OCR trust/review/storage integration; mocked recognition, temporary synthetic data.

Engine accuracy belongs to the OCR engine tests. These checks prove that recognition
cannot bypass review, source identity, transaction boundaries, export or recovery.
"""
import base64
from contextlib import contextmanager
from copy import deepcopy
from http.client import HTTPConnection
import importlib
import json
from pathlib import Path
import sys
import tempfile
import threading
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from access import AccessService, password_record
from audit_export import build_export, verify_export
from backup import verified_copy
from document_analysis import extract, sources
from domain import Store, WorkflowError
from server import EloServer

PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aL1kAAAAASUVORK5CYII=')
PDF = b'%PDF-1.4\n% Synthetic fixture: literal/OCR workers mocked in these tests.\n%%EOF'


def recognition(complete=True):
    return {'segments': [{'page': 1, 'location': 'Página 1, região 1',
                         'text': 'Contrato sintético CTR-1042', 'bbox': {'x': 0.1, 'y': 0.2, 'width': 0.6, 'height': 0.1},
                         'confidence': 0.95 if complete else 0.3}],
            'missing_pages': [], 'extraction_status': 'complete' if complete else 'inconclusive',
            'quality': {'assessment': 'review_required' if complete else 'inconclusive',
                        'minimum_confidence': 0.95 if complete else 0.3,
                        'mean_confidence': 0.95 if complete else 0.3, 'threshold': 0.8,
                        'confidence_note': 'Synthetic confidence for workflow testing', 'flags': [] if complete else ['low_confidence']},
            'pages': [{'page': 1, 'width': 1000, 'height': 800}],
            'engine': {'name': 'synthetic-test-engine', 'version': 'test-v1'}, 'limitations': 'OCR pode conter erros.'}


@contextmanager
def mocked_engine(result=None, side_effect=None):
    # Allows workflow tests during engine development without invoking an installed OCR binary.
    try:
        module = importlib.import_module('ocr')
    except ModuleNotFoundError as error:
        if error.name != 'ocr':
            raise
        module = types.ModuleType('ocr')
        module.extract = lambda *_: None
    with patch.dict(sys.modules, {'ocr': module}):
        with patch.object(module, 'extract', return_value=deepcopy(result or recognition()), side_effect=side_effect) as mocked:
            yield mocked


class OcrFixture(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.store = Store(self.root / 'source.sqlite3')
        self.store.apply('detect', {})

    def upload(self, pdf=False):
        return self.store.apply('evidence/upload', {'actor': 'Analista', 'case_id': 'ELO-1042',
            'synthetic': True, 'name': 'scan.pdf' if pdf else 'scan.png',
            'media_type': 'application/pdf' if pdf else 'image/png', 'description': 'Imagem sintética',
            'content_base64': base64.b64encode(PDF if pdf else PNG).decode()})['attachments'][-1]

    def analyze(self, metadata, result=None):
        with mocked_engine(result):
            analysis = extract(self.store.read(), metadata, PDF if metadata['media_type'] == 'application/pdf' else PNG, mode='ocr')
        return self.store.apply('document/record', {'actor': 'Analista', 'analysis': analysis})['document_analyses'][-1]

    def review(self, entry, **extra):
        return self.store.apply('evidence/review', {'actor': 'Revisor', 'analysis_id': entry['id'],
            'revision': entry['revision'], 'outcome': 'accepted', 'reason': 'Trechos conferidos na imagem original',
            'confirmed': True, **extra})


class OcrWorkflowTest(OcrFixture):
    def test_pending_ocr_is_not_a_source_and_requires_explicit_ocr_confirmation(self):
        entry = self.analyze(self.upload())
        self.assertEqual(entry['status'], 'pending')
        self.assertEqual(entry['method'], 'ocr')
        self.assertEqual(sources(self.store.read(), 'ELO-1042'), [])
        before = self.store.export_state()
        for confirmation in (None, False, 'true'):
            with self.subTest(confirmation=confirmation), self.assertRaises(WorkflowError):
                self.review(entry, confirmed_ocr=confirmation)
            self.assertEqual(self.store.export_state(), before)
        state = self.review(entry, confirmed_ocr=True)
        source = sources(state, 'ELO-1042')[0]
        self.assertIn('OCR', source['source'])
        self.assertIn('Página 1, região 1', source['detail'])
        self.assertTrue(state['document_analyses'][0]['review']['ocr_checked'])
        from consultation import context_for
        context = context_for(state, 'ELO-1042')
        captured = next(item for item in context['sources'] if item['id'] == source['id'])
        self.assertIn('OCR', captured['source'])
        self.assertIn('Página 1, região 1', captured['detail'])
        self.assertIn('OCR revisado', context['scope'])

    def test_low_confidence_or_missing_pages_block_acceptance(self):
        for result in (recognition(False), {**recognition(), 'missing_pages': [2]}):
            with self.subTest(result=result):
                entry = self.analyze(self.upload(), result)
                self.assertEqual(entry['extraction_status'], 'inconclusive')
                before = self.store.export_state()
                with self.assertRaises(WorkflowError):
                    self.review(entry, confirmed_ocr=True)
                self.assertEqual(self.store.export_state(), before)
                state = self.review(entry, outcome='rejected')
                self.assertEqual(state['document_analyses'][-1]['status'], 'rejected')
                self.assertEqual(sources(state, 'ELO-1042'), [])

    def test_ocr_after_literal_inconclusive_preserves_old_review_and_prevents_duplicate_method(self):
        metadata = self.upload(pdf=True)
        with patch('document_analysis._pdf', return_value={'segments': [], 'missing_pages': [1]}):
            literal = extract(self.store.read(), metadata, PDF)
        state = self.store.apply('document/record', {'actor': 'Analista', 'analysis': literal})
        state = self.review(state['document_analyses'][0], outcome='rejected')
        old = deepcopy(state['document_analyses'][0])
        entry = self.analyze(metadata)
        self.assertEqual(self.store.read()['document_analyses'][0], old)
        before = self.store.export_state()
        with self.assertRaises(WorkflowError):
            self.analyze(metadata)
        self.assertEqual(self.store.export_state(), before)
        state = self.review(entry, confirmed_ocr=True)
        self.assertEqual(state['document_analyses'][0], old)
        self.assertEqual(len(sources(state, 'ELO-1042')), 1)

    def test_never_accepts_two_methods_for_same_attachment(self):
        metadata = self.upload(pdf=True)
        with patch('document_analysis._pdf', return_value={'segments': [
                {'page': 1, 'location': 'Página 1', 'text': 'CTR-1042 sintético'}], 'missing_pages': []}):
            literal = extract(self.store.read(), metadata, PDF)
        state = self.store.apply('document/record', {'actor': 'Analista', 'analysis': literal})
        self.review(state['document_analyses'][0])
        entry = self.analyze(metadata)
        before = self.store.export_state()
        with self.assertRaises(WorkflowError):
            self.review(entry, confirmed_ocr=True)
        self.assertEqual(self.store.export_state(), before)
        self.assertEqual(len(sources(self.store.read(), 'ELO-1042')), 1)

    def test_source_locations_confidence_and_review_survive_restart_export_backup(self):
        entry = self.analyze(self.upload())
        self.review(entry, confirmed_ocr=True)
        before = self.store.export_state(include_files=True)
        self.assertEqual(Store(self.store.path).export_state(include_files=True), before)
        package = build_export(before)
        self.assertTrue(verify_export(package))
        self.assertEqual(package['state']['document_analyses'][0]['segments'], recognition()['segments'])
        altered = deepcopy(package)
        altered['state']['document_analyses'][0]['segments'][0]['bbox'] = [0, 0, 1, 1]
        self.assertFalse(verify_export(altered))
        verified_copy(self.store.path, self.root / 'restored.sqlite3')
        self.assertEqual(Store(self.root / 'restored.sqlite3').export_state(include_files=True), before)
        self.assertEqual(self.store.export_state(include_files=True), before)


class OcrHttpTest(OcrFixture):
    @classmethod
    def setUpClass(cls):
        cls.password = 'synthetic-test-password'
        cls.password_hash = password_record(cls.password)

    def setUp(self):
        super().setUp()
        self.metadata = self.upload()
        accounts = self.root / 'accounts.json'
        accounts.write_text(json.dumps({'version': 1, 'users': [
            {'id': role, 'name': role, 'roles': [role], 'active': True, 'password': self.password_hash}
            for role in ('analyst', 'reviewer', 'operator', 'auditor')]}))
        accounts.chmod(0o600)
        self.clock = [0]
        access = AccessService(accounts, clock=lambda: self.clock[0], session_ttl=30)
        self.server = EloServer(('127.0.0.1', 0), self.store, access_service=access)
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(lambda: (self.server.shutdown(), self.server.server_close(), thread.join()))

    def request(self, path, data, cookie=None):
        connection = HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        try:
            connection.request('POST', path, json.dumps(data), {'Content-Type': 'application/json', **({'Cookie': cookie} if cookie else {})})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), json.loads(response.read())
        finally:
            connection.close()

    def login(self, role):
        status, headers, _ = self.request('/api/login', {'username': role, 'password': self.password})
        self.assertEqual(status, 200)
        return headers['Set-Cookie'].split(';')[0]

    def test_http_ocr_roles_canonical_identity_and_forged_analysis(self):
        body = {'actor': 'admin', 'attachment_id': self.metadata['id'], 'mode': 'ocr',
                'analysis': {'text': 'FORGED', 'status': 'accepted', 'extraction_status': 'complete'}}
        before = self.store.export_state()
        with mocked_engine() as engine:
            self.assertEqual(self.request('/api/evidence/analyze', body)[0], 401)
            for role in ('operator', 'auditor'):
                cookie = self.login(role)
                self.assertEqual(self.request('/api/evidence/analyze', body, cookie)[0], 403)
                self.assertEqual(self.request('/api/evidence/review', {'actor': 'admin'}, cookie)[0], 403)
            engine.assert_not_called()
            self.assertEqual(self.store.export_state(), before)
            analyst = self.login('analyst')
            status, _, state = self.request('/api/evidence/analyze', body, analyst)
            self.assertEqual(status, 200)
            engine.assert_called_once_with(PNG, 'image/png')
        entry = state['document_analyses'][0]
        self.assertNotIn('FORGED', entry['text'])
        self.assertEqual(entry['status'], 'pending')
        self.assertEqual(entry['actor'], 'analyst')
        self.assertEqual(state['audit'][-1]['authentication'], {'mode': 'local-auth', 'user_id': 'analyst'})
        reviewer = self.login('reviewer')
        status, _, state = self.request('/api/evidence/review', {'actor': 'admin', 'analysis_id': entry['id'],
            'revision': entry['revision'], 'outcome': 'accepted', 'reason': 'Imagem conferida',
            'confirmed': True, 'confirmed_ocr': True}, reviewer)
        self.assertEqual(status, 200)
        self.assertEqual(state['document_analyses'][0]['review']['actor'], 'reviewer')

    def test_http_session_rechecked_after_ocr_and_lock_released_on_failure(self):
        analyst = self.login('analyst')
        before = self.store.export_state()
        def expire(*_):
            self.clock[0] = 31
            return recognition()
        body = {'attachment_id': self.metadata['id'], 'mode': 'ocr'}
        with mocked_engine(side_effect=expire):
            self.assertEqual(self.request('/api/evidence/analyze', body, analyst)[0], 401)
        self.assertEqual(self.store.export_state(), before)
        self.assertFalse(self.server.document_lock.locked())
        analyst = self.login('analyst')
        with mocked_engine(side_effect=WorkflowError('OCR inconclusivo', 409)):
            self.assertEqual(self.request('/api/evidence/analyze', body, analyst)[0], 409)
        self.assertFalse(self.server.document_lock.locked())
        self.assertEqual(self.store.export_state(), before)


if __name__ == '__main__':
    unittest.main()
