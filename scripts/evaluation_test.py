"""Metric regression tests, offline: no provider call or database."""
import unittest
from evaluation import score, summary, distance, normalize, digest
from evaluation_review import template, adjudicate


class EvaluationTests(unittest.TestCase):
    def test_anchor_with_wrong_source_does_not_count(self):
        case={'sources':[{'id':'A'},{'id':'B'}], 'facts':[{'id':'v','source_ids':['A'],'patterns':['731']}], 'abstain':False}
        result={'claims':[{'text':'731','source_ids':['B']}]}
        metrics=score(case,result)
        self.assertEqual(metrics['anchor_coverage']['numerator'],0)
        self.assertEqual(metrics['valid_reference_claims']['numerator'],1)
        self.assertEqual(metrics['semantic_support'],'pending_independent_review')

    def test_absence_is_not_division_by_zero_or_accuracy(self):
        metrics=score({'sources':[],'facts':[],'abstain':True},{'claims':[]})
        self.assertTrue(metrics['abstention_matches_expected'])
        self.assertIsNone(metrics['valid_reference_claims']['rate'])
        self.assertIsNone(metrics['anchor_coverage']['rate'])

    def test_failures_count_against_abstention_denominator(self):
        metrics=score({'sources':[],'facts':[],'abstain':True},{'claims':[]})
        result=summary([{'status':'ok','seconds':1,'metrics':metrics},{'status':'failed','seconds':30}])
        self.assertEqual(result['failures'],1)
        self.assertEqual(result['abstention_accuracy_proxy']['rate'],.5)
        self.assertEqual(result['latency_seconds']['p95'],30)

    def test_review_rejects_pending_or_changed_output(self):
        result={'claims':[{'text':'Valor 731','source_ids':['A']}]}
        report={'ai':{'rows':[{'id':'one','status':'ok','response_sha256':digest(result),'result':result,'case':{'facts':[{'id':'amount'}]}}], 'summary':{'failures':0}}}
        review=template(report)
        with self.assertRaises(ValueError): adjudicate(report,review)
        review.update(reviewer='Independent test reviewer',reviewer_type='independent_agent')
        review['cases'][0].update(claims=[{'index':0,'verdict':'supported','reason':'Source A explicitly says 731.'}],omitted_fact_ids=[],safe_limitations_and_suggestion=True,notes='Synthetic controlled case.')
        self.assertEqual(adjudicate(report,review)['supported_claims']['rate'],1)
        report['ai']['rows'][0]['result']['claims'][0]['text']='Wrong value'
        with self.assertRaises(ValueError): adjudicate(report,review)

    def test_cer_counts_substitution_insertion_deletion(self):
        self.assertEqual(distance('abc','axc'),1)
        self.assertEqual(distance('abc','abcx'),1)
        self.assertEqual(distance('abc','ac'),1)
        self.assertEqual(distance('','x'),1)
        self.assertEqual(normalize('A\n\tB'),'A B')
        self.assertNotEqual(normalize('ação'),normalize('acao'))


if __name__=='__main__': unittest.main()
