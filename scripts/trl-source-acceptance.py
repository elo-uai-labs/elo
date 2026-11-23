"""Execute synthetic-source acceptance with a separate HTTP service and temp SQLite."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'backend'))
began = time.monotonic()
suite = unittest.defaultTestLoader.discover(str(ROOT/'backend/tests'), pattern='test_synthetic_source.py')
result = unittest.TextTestRunner(verbosity=2).run(suite)
paths = ['backend/synthetic_source.py', 'backend/monitoring.py', 'backend/domain.py',
         'scripts/trl-source-server.py', 'backend/tests/test_synthetic_source.py']
report = {'scope': 'Synthetic loopback service, separate process, disposable SQLite; no CAIXA system or representative environment approval',
          'protocol': 'elo-synthetic-source-v1', 'commit_at_execution': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
          'tests': result.testsRun, 'passed': result.wasSuccessful(), 'failures': len(result.failures), 'errors': len(result.errors),
          'elapsed_seconds': time.monotonic()-began,
          'covered': ['two-page atomic import and detection', 'record IDs and counts reconciled', 'source provenance',
                      'same content idempotent after Store restart', 'concurrent duplicate yields one batch',
                      '401 no retry', '503 bounded retry and exhaustion', 'timeout bounded retry',
                      'schema version drift', 'snapshot drift', 'duplicate IDs across pages', 'missing foreign reference',
                      'count mismatch', 'byte limit', 'redirect rejected', 'non-loopback endpoint rejected', 'manual database CLI guard'],
          'source_sha256': {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in paths},
          'limits': ['Invented synthetic contract, not a CAIXA API', 'No SSO/MFA or TLS in loopback fixture',
                     'No source accuracy/authenticity assertion', 'No production throughput claim',
                     'Existing integration auto-detects two original rules; third experimental rule remains explicit',
                     'Self-authored acceptance is not independent review or human validation']}
output = ROOT/'output/validation/trl5/source-integration.json'
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
print(json.dumps({'output':str(output), 'passed':report['passed'], 'tests':report['tests']}))
raise SystemExit(0 if result.wasSuccessful() else 1)
