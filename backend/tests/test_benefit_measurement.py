import copy
import unittest
from scripts.benefit_measurement import summarize


class BenefitTests(unittest.TestCase):
    def pair(self):
        common = dict(pair_id='P1', participant_id='synthetic-1', task_id='C03', sample_sha256='a'*64,
                      wait_minutes='1', corrections='1', required_facts='4', complete_facts='4', evidence='fixture', synthetic='true')
        return [dict(common, phase='baseline', order='1', human_minutes='10'),
                dict(common, phase='elo', order='2', human_minutes='6')]

    def test_separates_synthetic_and_preserves_negative_results(self):
        rows = self.pair()
        rows[1].update(human_minutes='12', complete_facts='3')
        result = summarize(rows)
        self.assertEqual(result['paired_results'][0]['reduction_percent'], -20)
        self.assertEqual(result['groups']['synthetic']['completeness_worsened_pairs'], 1)
        self.assertIsNone(result['groups']['participant_recorded']['median_human_minutes_saved'])

    def test_zero_and_incomplete_not_fabricated(self):
        rows = self.pair()
        rows[0]['human_minutes'] = '0'
        self.assertIsNone(summarize(rows)['paired_results'][0]['reduction_percent'])
        result = summarize(rows[:1])
        self.assertEqual(result['incomplete_pair_ids'], ['P1'])
        self.assertEqual(result['paired_results'], [])

    def test_bad_pairs_and_measurements_rejected(self):
        for field, value in [('sample_sha256', 'b'*64), ('participant_id', 'other'),
                             ('order', '1'), ('required_facts', '0'), ('human_minutes', 'nan'),
                             ('wait_minutes', None), ('corrections', '1.5'), ('complete_facts', '5'), ('synthetic', 'false')]:
            rows = copy.deepcopy(self.pair())
            rows[1][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                summarize(rows)
        with self.assertRaises(ValueError):
            summarize(self.pair() * 2)
