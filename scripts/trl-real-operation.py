"""Opt-in authenticated OCR/OpenAI journey while three clients read; max two paid calls."""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('operation', ROOT/'scripts/trl-operation.py')
operation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(operation)
from ai_usage import summarize as summarize_usage
from audit_export import build_export, verify_export
from access_audit import AccessAudit, verify_package
from domain import Store


class RealExercise(operation.Exercise):
    def __init__(self, folder, real):
        super().__init__(folder)
        self.real = real
        self.paid_requests = 0

    def start(self, ttl=3600):
        # Base Exercise deliberately blanks the key. This test-only subclass opts in.
        env = dict(os.environ, ELO_ENV='test', ELO_REQUIRE_AUTH='1', ELO_AI_PROVIDER='openai',
                   OPENAI_API_KEY=os.environ.get('OPENAI_API_KEY', '') if self.real else '',
                   ELO_ON_DEVICE_BIN='', ELO_AUTH_USERS_FILE=str(self.users))
        self.process = subprocess.Popen([sys.executable, str(ROOT/'scripts/trl-operation-server.py'),
            '--port', str(self.port), '--db', str(self.db), '--users', str(self.users), '--ttl', str(ttl)],
            cwd=ROOT, env=env, stdout=self.log, stderr=self.log)
        began = time.monotonic()
        for _ in range(100):
            if self.process.poll() is not None:
                raise RuntimeError('Isolated real-test server failed to start')
            try:
                self.request(None, '/health', expected=200, phase='readiness')
                return time.monotonic()-began
            except (OSError, AssertionError):
                time.sleep(.1)
        raise RuntimeError('Isolated server readiness timeout')

    def request(self, role, path, data=None, **kwargs):
        if path in ('/api/dossier', '/api/assistant/query') and data and data.get('mode') == 'real':
            if not self.real or self.paid_requests >= 2:
                raise AssertionError('Paid-call cap or opt-in violation')
            self.paid_requests += 1  # Count attempts, including failures; never retry.
        return super().request(role, path, data, **kwargs)


def normalized(text):
    return ' '.join(unicodedata.normalize('NFC', text).split())


def run(x, report):
    x.start()
    for role in ('analyst', 'reviewer', 'auditor'):
        x.login(role)
    x.request('auditor', '/api/detect', {}, expected=403)
    state = x.request('analyst', '/api/detect', {})
    case_id = state['case']['id']
    corpus_path = ROOT/'tests/fixtures/trl-evaluation/ocr.json'
    corpus = json.loads(corpus_path.read_text())
    fixture = next(item for item in corpus['cases'] if item['file'] == 'table.png')
    content = (corpus_path.parent/fixture['file']).read_bytes()
    assert hashlib.sha256(content).hexdigest() == fixture['sha256'], 'Frozen OCR fixture changed'
    report['fixture'] = {'file': fixture['file'], 'sha256': fixture['sha256'],
                         'corpus_sha256': hashlib.sha256(corpus_path.read_bytes()).hexdigest(),
                         'reused_exposed_fixture': True, 'synthetic': True}
    state = x.request('analyst', '/api/evidence/upload', {'case_id': case_id, 'name': fixture['file'],
        'media_type': fixture['mime'], 'description': 'Fixture sintetica congelada para exercicio concorrente.',
        'synthetic': True, 'content_base64': base64.b64encode(content).decode()})
    attachment_id = state['attachments'][-1]['id']
    stop = threading.Event()
    started = time.monotonic()
    def reader(role):
        count = 0
        while not stop.is_set():
            x.request(role, '/api/state', phase='concurrent_read')
            count += 1
            stop.wait(.15)
        return count
    with ThreadPoolExecutor(max_workers=3) as pool:
        readers = [pool.submit(reader, role) for role in ('analyst', 'reviewer', 'auditor')]
        try:
            began = time.monotonic()
            state = x.request('analyst', '/api/evidence/analyze', {'attachment_id': attachment_id, 'mode': 'ocr'}, phase='ocr')
            report['ocr_seconds'] = time.monotonic()-began
            analysis = state['document_analyses'][-1]
            assert analysis['extraction_status'] == 'complete', 'Legible OCR fixture must be reviewable'
            assert normalized(' '.join(segment['text'] for segment in analysis['segments'])) == normalized(fixture['expected_text']), 'OCR fixture text differs from frozen expected text'
            x.request('auditor', '/api/evidence/review', {'analysis_id': analysis['id']}, expected=403)
            state = x.request('reviewer', '/api/evidence/review', {'analysis_id': analysis['id'], 'revision': analysis['revision'],
                'confirmed': True, 'confirmed_ocr': True, 'outcome': 'accepted',
                'reason': 'Ensaio automatizado: fixture sintetica comparada ao gabarito congelado; nao representa revisao humana real.'})
            assert state['document_analyses'][-1]['status'] == 'accepted'
            mode = 'real' if x.real else 'local'
            began = time.monotonic()
            state = x.request('analyst', '/api/dossier', {'case_id': case_id, 'mode': mode}, phase='dossier')
            report['dossier_seconds'] = time.monotonic()-began
            dossier = state['case']['dossier']
            known = {item['id'] for item in state['case']['evidence']}
            assert all(set(claim['source_ids']) <= known and claim['source_ids'] for claim in dossier['claims'])
            protected = {key: state[key] for key in ('cases', 'risks', 'dimensions', 'actions', 'work_items', 'reports')}
            began = time.monotonic()
            state = x.request('analyst', '/api/assistant/query', {'case_id': case_id, 'mode': mode,
                'question': f'Qual é o total registrado no quadro sintético de parcelas do documento {attachment_id}?'}, phase='assistant')
            report['assistant_seconds'] = time.monotonic()-began
            query = state['assistant_queries'][-1]
            assert not query['abstained']
            assert any(attachment_id in claim['source_ids'] and re.search(r'330[,.]00', claim['text']) for claim in query['claims']), 'Answer must cite reviewed OCR document for recorded total'
            assert {key: state[key] for key in protected} == protected, 'Assistant changed protected business state'
            if x.real:
                assert dossier.get('usage', {}).get('provider') == 'openai' and query.get('usage', {}).get('provider') == 'openai'
                assert dossier['usage']['total_tokens'] is not None and query['usage']['total_tokens'] is not None
            report['outputs'] = {'dossier': {'model': dossier['model'], 'prompt_version': dossier['prompt_version'],
                                'claims': dossier['claims'], 'usage': dossier.get('usage')},
                'assistant': {'model': query['model'], 'prompt_version': query['prompt_version'],
                              'claims': query['claims'], 'sources': query['sources'], 'usage': query.get('usage')},
                'ocr': {'text': analysis['text'], 'method': analysis['method'], 'metadata': analysis['ocr']}}
            report['checks'] = {'ocr_matches_frozen_text': True, 'reviewed_document_cited': True,
                'expected_total_present': True, 'protected_business_state_unchanged': True,
                'review_identity': 'synthetic automated reviewer; not human adjudication'}
        finally:
            stop.set()
            report['reader_counts'] = [future.result() for future in readers]
    report['concurrent_window_seconds'] = time.monotonic()-started
    before = Store(x.db).export_state(include_files=True)
    package = build_export(before)
    assert verify_export(package)
    report['usage_report'] = summarize_usage(package['events'])
    x.stop()
    x.start()
    assert Store(x.db).export_state(include_files=True) == before
    x.login('auditor')
    state = x.request('auditor', '/api/state')
    assert state['audit_valid']
    accesses = AccessAudit(x.db).export()
    assert verify_package(accesses)
    assert len(accesses['events']) == len(x.records)
    with sqlite3.connect(x.db) as connection:
        assert connection.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    report['integrity'] = {'restart_snapshot_identical': True, 'business_package_verified': True,
        'access_chain_verified': True, 'access_count_exact': True, 'sqlite_integrity': 'ok',
        'business_events': len(before['audit']), 'access_events': len(accesses['events'])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--smoke', action='store_true', help='OCR real local + synthese local; no OpenAI requests')
    mode.add_argument('--real', action='store_true')
    parser.add_argument('--allow-paid', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.real and (not args.allow_paid or not os.environ.get('OPENAI_API_KEY', '').strip() or not os.environ.get('ELO_MODEL', '').strip()):
        parser.error('Real run requires --allow-paid, OPENAI_API_KEY and ELO_MODEL; no request made')
    if args.smoke and args.allow_paid:
        parser.error('Smoke does not accept --allow-paid')
    report = {'date': datetime.now(timezone.utc).isoformat(), 'real_openai': args.real,
        'scope': 'Authenticated synthetic OCR and up to two OpenAI responses concurrent with three readers',
        'criteria_before_execution': {'unexpected_errors': 0, 'max_paid_attempts': 2,
            'reviewed_ocr_document_cited': True, 'provider_usage_audited': args.real,
            'integrity_and_restart': True, 'reads_p95_seconds_less_than': 2},
        'limits': ['Short observed window, not60seconds of sustained real-model load',
            'No IA/OCR latency percentile from one sample per operation', 'Known synthetic fixture, not a new holdout',
            'Automated reviewer under synthetic account, not human review', 'Local accounts and loopback, no SSO/MFA/TLS/cloud',
            'Default HTTP client timeout15s, provider timeout30s; failed request is not retried',
            'No population semantic accuracy or CAIXA/TRL5 certification'],
        'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [*sorted((ROOT/'backend').glob('*.py')), ROOT/'scripts/trl-operation.py',
                ROOT/'scripts/trl-operation-server.py', ROOT/'scripts/trl-real-operation.py', ROOT/'scripts/trl-real-operation.mjs']}}
    with tempfile.TemporaryDirectory(prefix='elo-trl-real-operation-') as folder:
        x = RealExercise(folder, args.real)
        try:
            run(x, report)
        except Exception as error:
            report['failure_type'] = type(error).__name__
            report['failure'] = str(error) if isinstance(error, AssertionError) else 'Operation failed; no secret or response body logged'
        finally:
            x.close()
        report['requests'] = x.records
        report['paid_attempts'] = x.paid_requests
    values = [r['seconds'] for r in report['requests'] if r['phase'] == 'concurrent_read']
    report['read_metrics'] = {'count': len(values), 'p50_seconds': operation.percentile(values,.5),
        'p95_seconds': operation.percentile(values,.95), 'maximum_seconds': max(values, default=None)}
    report['unexpected_errors'] = sum(r['error_type'] is not None for r in report['requests'])
    report['expected_denials'] = sum(r['expected_status'] == 403 and r['status'] == 403 for r in report['requests'])
    report['passed'] = ('failure_type' not in report and bool(values) and operation.percentile(values,.95) < 2
        and report['unexpected_errors'] == 0 and report['paid_attempts'] == (2 if args.real else 0))
    destination = args.output or ROOT/'output/validation/trl5'/('real-operation.json' if args.real else 'real-operation-smoke.json')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({key:report[key] for key in ('passed','real_openai','paid_attempts','read_metrics','unexpected_errors')},ensure_ascii=False))
    if 'failure' in report:
        print(report['failure'])
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
