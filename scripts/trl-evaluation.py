"""First-pass frozen synthetic holdout; explicit paid opt-in, no database/server."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import time
import evaluation
from evaluation_review import template

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'tests/fixtures/trl-evaluation'


def ocr_holdout():
    import ocr
    manifest = json.loads((FIXTURES/'ocr.json').read_text())
    rows = []
    for case in manifest['cases']:
        content = (FIXTURES/case['file']).read_bytes()
        if hashlib.sha256(content).hexdigest() != case['sha256']:
            raise ValueError('Frozen OCR fixture hash mismatch')
        started = time.monotonic()
        row = dict(case)
        try:
            result = ocr.extract(content, case['mime'])
            actual = '\n'.join(segment['text'] for segment in result['segments'])
            ref, normalized = evaluation.normalize(case['expected_text']), evaluation.normalize(actual)
            row.update(status='ok', actual_text=actual, character_errors=evaluation.distance(ref, normalized),
                       reference_characters=len(ref), extraction_status=result['extraction_status'],
                       triage_matches_expected=(result['extraction_status']=='inconclusive')==case['expected_inconclusive'],
                       engine=result['engine'], segments=result['segments'], quality=result['quality'])
        except Exception as error:
            row.update(status='failed', error_type=type(error).__name__)
        row['seconds'] = round(time.monotonic()-started,4)
        rows.append(row)
        print(f"OCR {case['file']}: {row['status']}", flush=True)
    legible = [r for r in rows if not r['expected_inconclusive'] and r['status']=='ok']
    denominator = sum(len(evaluation.normalize(r['expected_text'])) for r in rows if not r['expected_inconclusive'])
    # Failed legible inputs count all reference characters as errors, never silently excluded.
    errors = sum(r['character_errors'] if r['status']=='ok' else len(evaluation.normalize(r['expected_text'])) for r in rows if not r['expected_inconclusive'])
    summary = {'requests':len(rows),'failures':sum(r['status']!='ok' for r in rows),
               'legible_cer':evaluation.ratio(errors,denominator),
               'triage':evaluation.ratio(sum(r.get('triage_matches_expected',False) for r in rows),len(rows)),
               'blank_false_characters':sum(len(evaluation.normalize(r.get('actual_text',''))) for r in rows if not r['expected_text'])}
    criteria=manifest['criteria_before_execution']
    summary['automatic_passed'] = summary['failures']==0 and summary['legible_cer']['rate'] <= criteria['legible_cer_max'] and summary['triage']['rate']==criteria['triage_match_rate'] and summary['blank_false_characters']==criteria['blank_false_characters']
    return {'manifest':manifest,'manifest_sha256':evaluation.digest(manifest),'rows':rows,'summary':summary}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--real',action='store_true',help='Exactly 16 potentially paid OpenAI requests, no retries by this runner.')
    parser.add_argument('--ocr',action='store_true')
    parser.add_argument('--output',type=Path,required=True,help='New output directory; refuses to replace previous evaluation.')
    args=parser.parse_args()
    if not args.real and not args.ocr:parser.error('Choose explicit --real and/or --ocr')
    args.output.mkdir(parents=True,exist_ok=False)
    evaluation.FIXTURES=FIXTURES/'ai.json'
    fixture=json.loads(evaluation.FIXTURES.read_text())
    if len(fixture['cases'])!=16:raise ValueError('Frozen case count changed')
    report={'version':'elo-trl-evaluation-v1','created_at':datetime.now(timezone.utc).isoformat(),
            'scope':'New synthetic holdout first pass; no human validation or proven target-population representativeness. Do not equate valid references with semantic support.',
            'git_commit_at_execution':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'code_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['scripts/trl-evaluation.py','scripts/evaluation.py','backend/dossier.py','backend/consultation.py','backend/ocr.py']},
            'fixture_files_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(FIXTURES.iterdir()) if p.is_file()}}
    if args.real:
        report['ai']=evaluation.evaluate_ai()
        report['ai']['criteria_before_execution']=fixture['criteria_before_execution']
        summary=report['ai']['summary']
        summary['automatic_passed']=summary['failures']==0 and summary['valid_references']['rate']==1 and summary['abstention_accuracy_proxy']['rate']==1
        summary['semantic_acceptance']='pending_independent_review'
    if args.ocr:report['ocr']=ocr_holdout()
    (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    if args.real:(args.output/'review-template.json').write_text(json.dumps(template(report),ensure_ascii=False,indent=2)+'\n')
    print(args.output/'report.json')
    return int(any(not report[k]['summary']['automatic_passed'] for k in ('ai','ocr') if k in report))


if __name__=='__main__':raise SystemExit(main())
