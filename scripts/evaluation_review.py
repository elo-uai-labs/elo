"""Bind an explicit independent assessment to exact model outputs; never infer support."""
import argparse
import json
from pathlib import Path
from evaluation import digest, ratio


def template(report):
    return {'version':'elo-evaluation-review-v1','report_sha256':digest(report),
            'reviewer':'PENDING','reviewer_type':'PENDING','scope':'synthetic_only',
            'cases':[{'id':row['id'],'response_sha256':row['response_sha256'],
                      'claims':[{'index':i,'verdict':'pending','reason':''} for i,_ in enumerate(row['result']['claims'])],
                      'omitted_fact_ids':None,'safe_limitations_and_suggestion':None,'notes':''}
                     for row in report['ai']['rows'] if row['status']=='ok']}


def adjudicate(report, review):
    if review.get('report_sha256') != digest(report): raise ValueError('Review belongs to a different report')
    if review.get('reviewer_type') not in ('human','independent_agent') or not review.get('reviewer') or review['reviewer']=='PENDING':
        raise ValueError('Identify reviewer and distinguish human from independent_agent')
    rows={r['id']:r for r in report['ai']['rows'] if r['status']=='ok'}
    cases=review['cases']
    if len(cases)!=len(rows) or {r['id'] for r in cases}!=set(rows): raise ValueError('Incomplete or duplicate case review')
    total=supported=unsupported=unclear=omitted=facts=unsafe=0
    for case in cases:
        row=rows[case['id']]
        if case['response_sha256']!=row['response_sha256'] or row['response_sha256']!=digest(row['result']): raise ValueError('Changed model output')
        claims=case['claims']; count=len(row['result']['claims'])
        if len(claims)!=count or {c['index'] for c in claims}!=set(range(count)): raise ValueError('Incomplete or duplicate claim review')
        for claim in claims:
            if claim['verdict'] not in ('supported','unsupported','unclear') or not claim['reason'].strip(): raise ValueError('Explicit verdict and reason required')
            total+=1; supported+=claim['verdict']=='supported'; unsupported+=claim['verdict']=='unsupported'; unclear+=claim['verdict']=='unclear'
        expected={f['id'] for f in row['case']['facts']}
        omissions=case['omitted_fact_ids']
        if not isinstance(omissions,list) or len(omissions)!=len(set(omissions)) or not set(omissions)<=expected: raise ValueError('Invalid omission list')
        if type(case['safe_limitations_and_suggestion']) is not bool or not case['notes'].strip(): raise ValueError('Review safety and document reasoning')
        omitted+=len(omissions); facts+=len(expected); unsafe+=not case['safe_limitations_and_suggestion']
    return {'reviewer':review['reviewer'],'reviewer_type':review['reviewer_type'],
            'supported_claims':ratio(supported,total),'unsupported_claims':ratio(unsupported,total),
            'unclear_claims':ratio(unclear,total),'omitted_expected_facts':ratio(omitted,facts),
            'unsafe_limitations_or_suggestions':ratio(unsafe,len(cases)),
            'failures_excluded_from_claim_denominator':report['ai']['summary']['failures'],
            'warning':'Avaliação do conjunto sintético pelo revisor identificado; não é homologação humana/corporativa nem estimativa populacional.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report',type=Path)
    parser.add_argument('--review',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    report=json.loads(args.report.read_text())
    if args.review:
        review=json.loads(args.review.read_text())
        output={'report_sha256':digest(report),'review_sha256':digest(review),'summary':adjudicate(report,review)}
    else: output=template(report)
    args.output.write_text(json.dumps(output,ensure_ascii=False,indent=2))


if __name__=='__main__': main()
