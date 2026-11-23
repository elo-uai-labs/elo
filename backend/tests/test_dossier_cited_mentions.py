"""A mentioned entity is not a new source; only cited text may authorize its ID."""
import io
import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import dossier
from domain import WorkflowError


class DossierCitedMentionsTests(unittest.TestCase):
    def setUp(self):
        self.sources = [{'id': 'CTR-801', 'detail': 'Fornecedor FOR-801 e aprovador EMP-801.'},
                        {'id': 'CTR-802', 'detail': 'Fornecedor FOR-802 e risco RSK-802.'}]
        self.ids = [s['id'] for s in self.sources]
        self.output = {'claims': [{'text': 'CTR-801 menciona FOR-801 e EMP-801.', 'source_ids': ['CTR-801']}],
                       'limitations': 'Menção literal não comprova irregularidade.', 'suggestion': 'Conferir documentos.'}

    def generate(self, output, provider):
        if provider == 'apple':
            with patch('dossier.subprocess.run', return_value=SimpleNamespace(stdout=json.dumps({**output, 'model': 'test'}))):
                return dossier.generate_on_device('/test/model', self.sources, self.ids)
        response = {'status': 'completed', 'model': 'test', 'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps(output)}]}]}
        with patch.dict(os.environ, {'ELO_AI_PROVIDER': 'openai', 'OPENAI_API_KEY': 'synthetic', 'ELO_MODEL': 'test'}), patch('dossier.urlopen', return_value=io.BytesIO(json.dumps(response).encode())):
            return dossier.generate_real(self.sources, self.ids)

    def test_real_dossier_accepts_literal_mentions_in_cited_contract(self):
        for provider in ('openai', 'apple'):
            with self.subTest(provider=provider):
                result = self.generate(self.output, provider)
                self.assertEqual(result['claims'], self.output['claims'])
                self.assertEqual(result['source_ids'], ['CTR-801'])

    def test_uncited_mentions_invented_entities_and_new_source_ids_rejected(self):
        for claim in (
            {'text': 'FOR-802 aparece.', 'source_ids': ['CTR-801']},
            {'text': 'RSK-802 aparece.', 'source_ids': ['CTR-801']},
            {'text': 'EMP-999 aparece.', 'source_ids': ['CTR-801']},
            {'text': 'FOR-801 aparece.', 'source_ids': ['FOR-801']},
        ):
            for provider in ('openai', 'apple'):
                with self.subTest(provider=provider, claim=claim), self.assertRaises(WorkflowError):
                    self.generate({**self.output, 'claims': [claim]}, provider)
