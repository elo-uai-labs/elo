"""Citations remain source IDs; literal document mentions need cited support."""
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from subprocess import CompletedProcess
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dossier
from consultation import answer
from domain import WorkflowError


class DocumentGroundingTest(unittest.TestCase):
    def setUp(self):
        self.sources = [
            {'id': 'EVD-0001', 'source': 'TXT revisado', 'detail': 'Ata menciona FOR-042 e FOR-UNKNOWN.'},
            {'id': 'EVD-0002', 'source': 'TXT revisado', 'detail': 'Outra ata menciona FOR-999.'}]
        self.context = {'sources': self.sources, 'mode': 'local', 'question': 'FOR-042',
            'case_id': 'ELO-1042', 'context_hash': 'hash', 'captured_at': 'now', 'partial': False, 'scope': 'test'}
        self.output = {'claims': [{'text': 'Ata menciona FOR-042 e FOR-UNKNOWN.', 'source_ids': ['EVD-0001']}],
                       'limitations': 'Menções não comprovam fatos.', 'suggestion': 'Confira o original.'}

    def test_local_literal_and_real_grounded_provider(self):
        local = answer(self.context)
        self.assertEqual(local['claims'][0]['source_ids'], ['EVD-0001'])
        output = {**self.output, 'model': 'test'}
        with patch.dict(os.environ, {'ELO_ON_DEVICE_BIN': '/mock/local-model'}), patch('dossier.subprocess.run', return_value=CompletedProcess([], 0, json.dumps(output), '')):
            real = answer({**self.context, 'mode': 'real'})
        self.assertEqual(real['claims'], self.output['claims'])
        # A base dossier retains its prior strict entity validation.
        with self.assertRaises(ValueError):
            dossier.verified_dossier(self.output, 'test', ['EVD-0001', 'EVD-0002'])

    def test_uncited_invented_and_mention_as_citation_rejected(self):
        for text, ids in [('FOR-INVENTED', ['EVD-0001']), ('FOR-999', ['EVD-0001']),
                          ('FOR-042', ['FOR-042']), ('EVD-0002', ['EVD-0001']),
                          *[(prefix + '-INVENTED', ['EVD-0001']) for prefix in ('WRK', 'DOC', 'ASK', 'BAT')]]:
            output = {**self.output, 'claims': [{'text': text, 'source_ids': ids}]}
            with self.subTest(text=text, ids=ids):
                with self.assertRaises(ValueError):
                    dossier.verified_dossier(output, 'test', ['EVD-0001', 'EVD-0002'], evidence=self.sources)
                with self.assertRaises(WorkflowError):
                    answer({**self.context, 'mode': 'real'}, generator=lambda *_: {**output, 'model': 'test', 'mode': 'real'})

    def test_new_product_identifiers_require_literal_cited_support(self):
        literal = 'Menções WRK-001 DOC-001 ASK-001 BAT-001.'
        sources = [{'id': 'EVD-0001', 'source': 'TXT revisado', 'detail': literal}]
        output = {**self.output, 'claims': [{'text': literal, 'source_ids': ['EVD-0001']}]}
        self.assertEqual(dossier.verified_dossier(output, 'test', ['EVD-0001'], evidence=sources)['claims'], output['claims'])
        result = answer({**self.context, 'sources': sources, 'mode': 'real'}, generator=lambda *_: {**output, 'model': 'test', 'mode': 'real'})
        self.assertEqual(result['claims'], output['claims'])
