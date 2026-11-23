"""Run frozen independently authored OCR corpus once into a new output directory."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
import statistics
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('trl_evaluation', ROOT/'scripts/trl-evaluation.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
runner.FIXTURES = ROOT/'tests/fixtures/independent-validation/ocr'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    report = {
        'version': 'elo-independent-ocr-evaluation-v1',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'scope': 'Independent synthetic authorship, not human/domain or population validation. First pass is retained, including failures.',
        'git_commit_at_execution': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'code_sha256': {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['backend/ocr.py', 'scripts/evaluation.py', 'scripts/trl-evaluation.py', 'scripts/independent-ocr-evaluation.py']},
        'ocr': runner.ocr_holdout(),
    }
    durations = sorted(row['seconds'] for row in report['ocr']['rows'])
    report['performance'] = {
        'requests': len(durations), 'declared_input_pages': {row['file']: (2 if row['file'] == 'partial.pdf' else 1) for row in report['ocr']['rows']}, 'seconds_p50': statistics.median(durations),
        'seconds_p95_nearest_rank': durations[math.ceil(0.95*len(durations))-1],
        'seconds_max': max(durations), 'budget_per_file_seconds': 30,
        'all_durations_within_budget': all(value <= 30 for value in durations),
        'warmup': False, 'scope': 'Sequential local corpus; no concurrency or production capacity claim',
    }
    (args.output/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(report['ocr']['summary'], ensure_ascii=False))
    return int(not report['ocr']['summary']['automatic_passed'])


if __name__ == '__main__':
    raise SystemExit(main())
