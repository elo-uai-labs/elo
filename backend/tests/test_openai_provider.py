"""Provider routing and API contract, with no network or real credentials."""
import io
import json
import os
import unittest
from unittest.mock import patch
from urllib.error import URLError

import dossier
from domain import WorkflowError


class OpenAIProviderTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            'ELO_AI_PROVIDER': 'openai', 'OPENAI_API_KEY': 'test-only',
            'ELO_MODEL': 'gpt-6.1-terra', 'ELO_ON_DEVICE_BIN': '/must-not-run',
        }, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.sources = [{'id': 'CTR-001', 'detail': 'Contrato sintético.'}]
        self.output = {'claims': [{'text': 'Contrato sintético.', 'source_ids': ['CTR-001']}],
                       'limitations': 'Dados sintéticos.', 'suggestion': 'Revisar evidências.'}

    def response(self, status='completed'):
        return io.BytesIO(json.dumps({'status': status, 'model': 'gpt-6.1-terra', 'output': [
            {'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps(self.output)}]}
        ]}).encode())

    def test_openai_wins_over_installed_apple_for_dossier_and_assistant(self):
        for question in (None, 'O que consta?'):
            with self.subTest(question=question), patch('dossier.urlopen', return_value=self.response()) as request, patch('dossier.generate_on_device') as apple:
                result = dossier.generate_real(self.sources, ['CTR-001'], question=question)
                apple.assert_not_called()
                self.assertEqual(result['source_ids'], ['CTR-001'])
                req = request.call_args.args[0]
                self.assertEqual(req.full_url, 'https://api.openai.com/v1/responses')
                self.assertEqual(req.get_header('Authorization'), 'Bearer test-only')
                body = json.loads(req.data)
                self.assertFalse(body['store'])
                self.assertEqual(body['model'], 'gpt-6.1-terra')
                self.assertTrue(body['text']['format']['strict'])
                self.assertEqual(body['max_output_tokens'], 8192)
                self.assertNotIn('test-only', req.data.decode())
                if question:
                    self.assertEqual(json.loads(body['input'])['question'], question)

    def test_missing_key_does_not_fallback_or_call_network(self):
        for key in ('', '   '):
            with patch.dict(os.environ, {'OPENAI_API_KEY': key}), patch('dossier.urlopen') as request, patch('dossier.generate_on_device') as apple:
                self.assertFalse(dossier.configured())
                with self.assertRaises(WorkflowError) as error:
                    dossier.generate_real(self.sources, ['CTR-001'])
                self.assertEqual(error.exception.status, 503)
                request.assert_not_called()
                apple.assert_not_called()

    def test_invalid_provider_fails_closed(self):
        with patch.dict(os.environ, {'ELO_AI_PROVIDER': 'typo'}), patch('dossier.urlopen') as request:
            self.assertFalse(dossier.configured())
            with self.assertRaises(WorkflowError): dossier.generate_real(self.sources, ['CTR-001'])
            request.assert_not_called()

    def test_apple_and_auto_preserve_local_provider(self):
        for name in ('apple', 'auto'):
            with patch.dict(os.environ, {'ELO_AI_PROVIDER': name}), patch('dossier.generate_on_device', return_value={'local': True}) as apple, patch('dossier.urlopen') as request:
                self.assertTrue(dossier.configured())
                self.assertEqual(dossier.generate_real(self.sources, ['CTR-001']), {'local': True})
                apple.assert_called_once()
                request.assert_not_called()

    def test_explicit_apple_missing_binary_does_not_use_openai(self):
        with patch.dict(os.environ, {'ELO_AI_PROVIDER': 'apple', 'ELO_ON_DEVICE_BIN': ''}), patch('dossier.urlopen') as request:
            self.assertFalse(dossier.configured())
            with self.assertRaises(WorkflowError): dossier.generate_real(self.sources, ['CTR-001'])
            request.assert_not_called()

    def test_incomplete_and_invalid_citations_rejected(self):
        for status in ('incomplete', 'failed', 'completed'):
            if status == 'completed': self.output['claims'][0]['source_ids'] = ['UNKNOWN']
            with patch('dossier.urlopen', return_value=self.response(status)), self.assertRaises(WorkflowError) as error:
                dossier.generate_real(self.sources, ['CTR-001'])
            self.assertEqual(error.exception.status, 502)

    def test_network_error_does_not_fallback_or_leak_details(self):
        with patch('dossier.urlopen', side_effect=URLError('test-only')), patch('dossier.generate_on_device') as apple:
            with self.assertRaises(WorkflowError) as error: dossier.generate_real(self.sources, ['CTR-001'])
            self.assertNotIn('test-only', str(error.exception))
            apple.assert_not_called()
