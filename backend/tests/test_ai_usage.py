"""Token counters are provider metadata, never inferred from prose or invoices."""
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import ai_usage
import consultation
import dossier
from domain import Store, WorkflowError


class UsageTests(unittest.TestCase):
    def raw(self):
        return {'input_tokens': 100, 'input_tokens_details': {'cached_tokens': 20},
                'output_tokens': 40, 'output_tokens_details': {'reasoning_tokens': 30}, 'total_tokens': 140,
                'secret_unknown_field': 'must-not-persist'}

    def test_subset_tokens_not_added_twice_and_unknown_fields_removed(self):
        usage = ai_usage.openai_usage(self.raw())
        self.assertEqual(usage['status'], 'complete')
        self.assertEqual(usage['total_tokens'], 140)
        self.assertNotIn('secret_unknown_field', usage)
        self.assertTrue(ai_usage.valid_usage(usage))

    def test_missing_invalid_partial_and_zero_remain_distinct(self):
        self.assertEqual(ai_usage.openai_usage(None)['status'], 'missing')
        partial = ai_usage.openai_usage({'input_tokens': 0})
        self.assertEqual(partial['input_tokens'], 0)
        self.assertIsNone(partial['output_tokens'])
        self.assertEqual(partial['status'], 'partial')
        for changes in ({'input_tokens': True}, {'output_tokens': -1}, {'total_tokens': 141},
                        {'input_tokens_details': {'cached_tokens': 101}}, {'output_tokens_details': []}):
            result = ai_usage.openai_usage({**self.raw(), **changes})
            self.assertEqual(result['status'], 'invalid')
            self.assertTrue(all(result[key] is None for key in ai_usage.FIELDS))

    def test_estimate_is_explicit_and_cached_input_and_reasoning_not_double_charged(self):
        event = {'seq': 1, 'at': 'synthetic', 'action': 'Dossiê registrado', 'details': {'mode': 'real', 'model': 'test', 'usage': ai_usage.openai_usage(self.raw())}}
        historical = {**event, 'seq': 2, 'details': {'mode': 'real', 'model': 'test'}}
        rates = {'test': {'currency': 'USD', 'input_per_million': '2', 'cached_input_per_million': '1', 'output_per_million': '5'}}
        report = ai_usage.summarize([event, historical], rates)
        self.assertEqual(report['estimated_cost_by_currency']['USD'], '0.00038')
        self.assertEqual(report['records_without_cost_estimate'], 1)
        self.assertEqual(report['totals']['total_tokens'], {'reported_sum': 140, 'measured_records': 1, 'unmeasured_records': 1})
        self.assertEqual(ai_usage.summarize([event])['estimated_cost_by_currency'], {})
        for bad in ('NaN', 'Infinity', '-1', True):
            with self.assertRaises(ValueError):
                ai_usage.summarize([event], {'test': {**rates['test'], 'output_per_million': bad}})

    def test_openai_dossier_and_assistant_usage_survive_audited_export_and_restart(self):
        with tempfile.TemporaryDirectory() as temp:
            store = Store(Path(temp) / 'test.sqlite3')
            state = store.read()
            state = store.apply('detect', {'actor': 'Teste'})
            case = state['case']
            output = {'claims': [{'text': 'Registro sintético.', 'source_ids': [case['evidence'][0]['id']]}],
                      'limitations': 'Dados sintéticos.', 'suggestion': 'Revisão humana.'}
            response = {'status': 'completed', 'model': 'test', 'usage': self.raw(), 'output': [
                {'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps(output)}]}]}
            with patch.dict(os.environ, {'ELO_AI_PROVIDER': 'openai', 'OPENAI_API_KEY': 'fake', 'ELO_MODEL': 'test'}), patch('dossier.urlopen', side_effect=lambda *a, **k: io.BytesIO(json.dumps(response).encode())):
                generated = dossier.generate(case['evidence'], 'real')
                for _ in range(2):
                    state = store.apply('dossier', {**generated, 'case_id': case['id']})
                context = consultation.prepare(state, {'case_id': case['id'], 'question': 'O que consta?', 'mode': 'real'})
                answered = consultation.answer(context)
                state = store.apply('assistant/record', {'actor': 'Teste', 'answer': answered})
            restarted = Store(Path(temp) / 'test.sqlite3').read()
            self.assertTrue(restarted['audit_valid'])
            self.assertEqual(restarted['assistant_queries'][0]['usage'], generated['usage'])
            from audit_export import build_export, verify_export
            package = build_export(store.export_state(include_files=True))
            self.assertTrue(verify_export(package))
            report = ai_usage.summarize(package['events'])
            self.assertEqual(len(report['records']), 3)
            self.assertEqual(report['totals']['total_tokens']['reported_sum'], 420)
            self.assertNotIn('must-not-persist', json.dumps(restarted))
            with self.assertRaises(WorkflowError):
                consultation.answer(context, generator=lambda *args: {**generated, 'usage': {'provider': 'openai', 'secret': 'fake'}})


if __name__ == '__main__':
    unittest.main()
