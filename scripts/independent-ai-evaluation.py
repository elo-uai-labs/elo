"""One frozen, independently authored synthetic sample; 18 explicit paid calls, no retries."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import evaluation
from evaluation_review import template

ROOT=Path(__file__).resolve().parents[1]
FIXTURE=ROOT/'tests/fixtures/independent-validation/ai.json'
FREEZE=FIXTURE.with_name('ai-freeze.json')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--real',action='store_true')
    parser.add_argument('--allow-paid',action='store_true')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if not (args.real and args.allow_paid):parser.error('Both --real and --allow-paid are required')
    freeze=json.loads(FREEZE.read_text())
    if hashlib.sha256(FIXTURE.read_bytes()).hexdigest()!=freeze['fixture_sha256']:raise ValueError('Frozen fixture changed')
    fixture=json.loads(FIXTURE.read_text())
    if len(fixture['cases'])!=18 or len({c['id'] for c in fixture['cases']})!=18:raise ValueError('Frozen count changed')
    import dossier
    if not dossier.configured() or dossier.provider()!='openai':raise ValueError('Explicit configured OpenAI required')
    args.output.mkdir(parents=True,exist_ok=False)
    evaluation.FIXTURES=FIXTURE
    report={'version':'elo-independent-ai-evaluation-v1','created_at':datetime.now(timezone.utc).isoformat(),
            'scope':fixture['scope'],'freeze':freeze,
            'git_commit_at_execution':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'code_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['scripts/independent-ai-evaluation.py','scripts/evaluation.py','backend/dossier.py','backend/consultation.py']}}
    report['ai']=evaluation.evaluate_ai()
    report['ai']['criteria_before_execution']=fixture['criteria_before_execution']
    s=report['ai']['summary']
    s['automatic_passed']=s['failures']==0 and s['valid_references']['rate']==1 and s['abstention_accuracy_proxy']['rate']==1 and s['latency_seconds']['max']<=30
    s['semantic_acceptance']='pending_independent_review'
    (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (args.output/'review-template.json').write_text(json.dumps(template(report),ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(s,ensure_ascii=False,indent=2))
    return int(not s['automatic_passed'])


if __name__=='__main__':raise SystemExit(main())
