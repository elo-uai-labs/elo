"""Explicit bounded regression against already exposed fixtures; not a new holdout."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import evaluation
from evaluation_review import template

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--real',action='store_true',required=True)
parser.add_argument('--case',action='append',required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
fixture_path=ROOT/'tests/fixtures/trl-evaluation/ai.json'
fixture=json.loads(fixture_path.read_text())
known={case['id']:case for case in fixture['cases']}
if len(args.case)>4 or len(set(args.case))!=len(args.case) or not set(args.case)<=set(known):
    parser.error('Select one to four unique known cases; never retries implicitly')
args.output.mkdir(parents=True,exist_ok=False)
with tempfile.TemporaryDirectory(prefix='elo-regression-fixture-') as temp:
    path=Path(temp)/'selected.json'
    path.write_text(json.dumps({**fixture,'version':fixture['version']+'-exposed-regression','cases':[known[key] for key in args.case]},ensure_ascii=False))
    evaluation.FIXTURES=path
    report={'version':'elo-trl-regression-v1','created_at':datetime.now(timezone.utc).isoformat(),
            'scope':'Regression on already exposed cases; does not replace first-pass evaluation or establish holdout accuracy.',
            'original_fixture_sha256':hashlib.sha256(fixture_path.read_bytes()).hexdigest(),
            'git_commit_at_execution':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'code_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['scripts/trl-evaluation-regression.py','scripts/evaluation.py','backend/dossier.py','backend/consultation.py']},
            'ai':evaluation.evaluate_ai()}
(args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
(args.output/'review-template.json').write_text(json.dumps(template(report),ensure_ascii=False,indent=2)+'\n')
print(args.output/'report.json')
raise SystemExit(int(report['ai']['summary']['failures']>0))
