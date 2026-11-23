#!/usr/bin/env python3
"""Authenticated mixed HTTP exercise, exclusively temporary synthetic data."""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
from http.client import HTTPConnection
import json
import math
import os
from pathlib import Path
import secrets
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from access import provision
from access_audit import AccessAudit, verify_package
from audit_export import verify_export
from backup import verified_copy
from domain import Store


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def percentile(values, fraction):
    return sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)] if values else None


class Exercise:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.db = self.folder / 'operation.sqlite3'
        self.users = self.folder / 'accounts.json'
        self.passwords = {role: secrets.token_urlsafe(24) for role in ('analyst', 'reviewer', 'operator', 'auditor', 'admin')}
        for role, password in self.passwords.items():
            provision(self.users, role, f'{role} sintético', [role], password)
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            self.port = probe.getsockname()[1]
        self.cookies, self.records = {}, []
        self.metrics_lock = threading.Lock()
        self.process = None
        self.log = (self.folder / 'server.log').open('wb')

    def start(self, ttl=3600):
        env = dict(os.environ, ELO_ENV='test', ELO_REQUIRE_AUTH='1', ELO_AI_PROVIDER='openai',
                   OPENAI_API_KEY='', ELO_ON_DEVICE_BIN='', ELO_AUTH_USERS_FILE=str(self.users))
        self.process = subprocess.Popen([sys.executable, str(ROOT / 'scripts/trl-operation-server.py'),
            '--port', str(self.port), '--db', str(self.db), '--users', str(self.users), '--ttl', str(ttl)],
            cwd=ROOT, env=env, stdout=self.log, stderr=self.log)
        started = time.monotonic()
        for _ in range(100):
            if self.process.poll() is not None:
                raise RuntimeError('Isolated server failed to start')
            try:
                self.request(None, '/health', expected=200, phase='readiness')
                return time.monotonic() - started
            except (OSError, AssertionError):
                time.sleep(.1)
        raise RuntimeError('Readiness timeout')

    def stop(self, crash=False):
        if self.process and self.process.poll() is None:
            self.process.kill() if crash else self.process.terminate()
            self.process.wait(timeout=10)

    def request(self, role, path, data=None, expected=200, phase='journey', cookie=None):
        connection = HTTPConnection('127.0.0.1', self.port, timeout=15)
        headers = {'Content-Type': 'application/json', 'Origin': f'http://127.0.0.1:{self.port}'}
        selected = cookie if cookie is not None else self.cookies.get(role)
        if selected:
            headers['Cookie'] = selected
        began = time.monotonic()
        status, result, error = None, None, None
        try:
            connection.request('POST' if data is not None else 'GET', path,
                               json.dumps(data) if data is not None else None, headers)
            response = connection.getresponse()
            status = response.status
            raw = response.read()
            result = json.loads(raw) if raw else None
            if path == '/api/login' and status == 200:
                self.cookies[role] = response.getheader('Set-Cookie').split(';')[0]
            if status != expected:
                raise AssertionError(f'{path}: expected {expected}, received {status}')
            return result
        except Exception as exc:
            error = type(exc).__name__
            raise
        finally:
            connection.close()
            if phase != 'readiness':
                with self.metrics_lock:
                    self.records.append({'phase': phase, 'route': path.split('?')[0],
                        'method': 'POST' if data is not None else 'GET', 'role': role,
                        'seconds': time.monotonic()-began, 'status': status,
                        'expected_status': expected, 'error_type': error})

    def login(self, role):
        self.request(role, '/api/login', {'username': role, 'password': self.passwords[role]})

    def close(self):
        self.stop()
        self.log.close()


def journey(exercise):
    x = exercise
    x.request(None, '/api/state', expected=401)
    for role in x.passwords:
        x.login(role)
    x.request('auditor', '/api/detect', {}, expected=403)
    contracts = [{'id': f'CTR-TRL-{i:03}', 'supplier_id': 'FOR-031', 'approver_id': 'EMP-014',
                  'title': f'Contrato operacional sintético {i}'} for i in range(30)]
    x.request('analyst', '/api/import', {'synthetic': True, 'dataset': {'employees': [], 'suppliers': [], 'contracts': contracts}})
    state = x.request('analyst', '/api/detect', {})
    case = state['case']
    case_id = case['id']
    state = x.request('analyst', '/api/dossier', {'mode': 'local', 'case_id': case_id})
    case = state['case']
    state = x.request('analyst', '/api/decision', {'actor': 'forged', 'case_id': case_id,
        'dossier_revision': case['dossier']['revision'], 'linkage_revision': case['linkage_revision'],
        'review': 'adjust', 'outcome': 'qualify', 'reason': 'Revisão sintética do fluxo operacional.'})
    assert state['case']['decision']['actor'] == 'analyst'
    x.request('analyst', '/api/impact', {'case_id': case_id, 'kind': 'risk', 'outcome': 'approved', 'reason': 'Negativa de segregação.'}, expected=403)
    for kind in ('risk', 'maturity'):
        x.request('reviewer', '/api/impact', {'case_id': case_id, 'kind': kind, 'outcome': 'approved', 'reason': 'Revisão independente sintética.'})
    state = x.request('analyst', '/api/action', {'case_id': case_id, 'title': 'Plano operacional sintético', 'owner': 'operator', 'due': '2030-12-31'})
    action = state['actions'][-1]
    evidence = b'Evidencia sintetica: revisao operacional CTR-1042, sem conclusao automatica.'
    state = x.request('operator', '/api/evidence/upload', {'case_id': case_id, 'action_id': action['id'],
        'name': 'operacao.txt', 'media_type': 'text/plain', 'description': 'Documento inteiramente sintetico.',
        'synthetic': True, 'content_base64': base64.b64encode(evidence).decode()})
    attachment = state['attachments'][-1]
    state = x.request('analyst', '/api/evidence/analyze', {'attachment_id': attachment['id'], 'mode': 'literal'})
    analysis = state['document_analyses'][-1]
    review = {'analysis_id': analysis['id'], 'revision': analysis['revision'], 'confirmed': True,
              'outcome': 'accepted', 'reason': 'Texto conferido com documento sintetico.'}
    x.request('reviewer', '/api/evidence/review', review)
    x.request('reviewer', '/api/evidence/review', review, expected=409)
    state = x.request('operator', '/api/action/update', {'id': action['id'], 'case_id': case_id,
        'action_revision': action['revision'], 'status': 'closure_requested', 'evidence': 'Anexo sintetico conferido.'})
    action = state['actions'][-1]
    x.request('reviewer', '/api/action/close', {'id': action['id'], 'case_id': case_id,
        'action_revision': action['revision'], 'outcome': 'approved', 'reason': 'Encerramento independente sintetico.'})
    state = x.request('admin', '/api/report/create', {'title': 'Relatorio operacional sintetico', 'case_ids': [case_id]})
    report = state['reports'][-1]
    payload = {'id': report['id'], 'report_revision': report['revision'], 'outcome': 'approved', 'reason': 'Fontes conferidas.'}
    x.request('admin', '/api/report/review', payload, expected=403)
    x.request('reviewer', '/api/report/review', payload)
    state = x.request('analyst', '/api/assistant/query', {'case_id': case_id, 'mode': 'local', 'question': 'Qual é o contrato?'})
    assert state['assistant_queries'][-1]['mode'] == 'local'
    return case_id


def mixed(exercise, case_id, duration):
    x = exercise
    start = time.monotonic()
    deadline = start + duration
    def reader(role):
        routes = ['/api/state', '/api/work/summary', '/api/supervision']
        index = 0
        while time.monotonic() < deadline:
            x.request(role, routes[index % len(routes)], phase='mixed')
            index += 1
            time.sleep(.2)
    def writer():
        index = 0
        while time.monotonic() < deadline:
            state = x.request('analyst', '/api/work/create', {'title': f'Trabalho misto {index}',
                'description': 'Ensaio sintetico de escrita com leituras concorrentes.', 'owner': 'operator',
                'due': '2030-12-31', 'priority': 'normal', 'priority_reason': 'Prioridade experimental.',
                'case_ids': [case_id], 'reason': 'Planejamento sintetico.'}, phase='mixed')
            item = state['work_items'][-1]
            state = x.request('operator', '/api/work/status', {'id': item['id'], 'revision': item['revision'],
                'status': 'in_progress', 'reason': 'Inicio sintetico.'}, phase='mixed')
            current = state['work_items'][-1]
            x.request('operator', '/api/work/status', {'id': item['id'], 'revision': item['revision'],
                'status': 'completed', 'result': 'Resultado stale', 'reason': 'Conflito esperado.'}, expected=409, phase='mixed')
            x.request('operator', '/api/work/status', {'id': item['id'], 'revision': current['revision'],
                'status': 'completed', 'result': 'Resultado sintetico conferido.', 'reason': 'Conclusao sintetica.'}, phase='mixed')
            if index % 10 == 0:
                contract_id = f'CTR-TRLLOAD-{index:03}'
                x.request('analyst', '/api/import', {'synthetic': True, 'dataset': {'employees': [], 'suppliers': [],
                    'contracts': [{'id': contract_id, 'supplier_id': 'FOR-031', 'approver_id': 'EMP-014',
                                   'title': f'Ingestao durante carga sintetica {index}'}]}}, phase='mixed')
                x.request('analyst', '/api/detect', {}, phase='mixed')
                x.request('analyst', '/api/dossier', {'mode': 'local', 'case_id': 'ELO-' + contract_id.removeprefix('CTR-')}, phase='mixed')
            if index % 5 == 0:
                document = f'Evidencia sintetica mista {index}: contrato CTR-1042 revisado.'
                state = x.request('analyst', '/api/evidence/upload', {'case_id': case_id,
                    'name': f'misto-{index}.txt', 'media_type': 'text/plain', 'description': 'Sintetico durante carga.',
                    'synthetic': True, 'content_base64': base64.b64encode(document.encode()).decode()}, phase='mixed')
                attachment = state['attachments'][-1]
                state = x.request('analyst', '/api/evidence/analyze', {'attachment_id': attachment['id'], 'mode': 'literal'}, phase='mixed')
                analysis = state['document_analyses'][-1]
                x.request('reviewer', '/api/evidence/review', {'analysis_id': analysis['id'], 'revision': analysis['revision'],
                    'confirmed': True, 'outcome': 'accepted', 'reason': 'Conferencia automatizada de fixture literal sintetica.'}, phase='mixed')
                x.request('analyst', '/api/assistant/query', {'case_id': case_id, 'mode': 'local', 'question': 'Qual é o contrato?'}, phase='mixed')
            index += 1
            time.sleep(.5)
        return index
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(reader, role) for role in ('analyst', 'reviewer', 'auditor')]
        writes = pool.submit(writer)
        for future in futures:
            future.result()
        completed = writes.result()
    return {'scheduled_seconds': duration, 'elapsed_seconds': time.monotonic()-start,
            'reader_clients': 3, 'writer_clients': 1, 'completed_work_cycles': completed}


def recovery(x):
    # Quiescent acknowledged state: this does not claim kill-in-the-middle atomicity.
    before = Store(x.db).export_state(include_files=True)
    ledger_before = AccessAudit(x.db).export()
    old_cookie = x.cookies['analyst']
    x.stop(crash=True)
    restart_seconds = x.start()
    x.request(None, '/api/state', cookie=old_cookie, expected=401, phase='recovery')
    x.login('auditor')
    x.request('auditor', '/api/state', phase='recovery')
    after = Store(x.db).export_state(include_files=True)
    assert before == after
    assert verify_package(AccessAudit(x.db).export())
    x.stop()
    original_hash = hashlib.sha256(x.db.read_bytes()).hexdigest()
    backup, restored = x.folder / 'backup.sqlite3', x.folder / 'restored.sqlite3'
    began = time.monotonic()
    verified_copy(x.db, backup)
    verified_copy(backup, restored)
    restore_seconds = time.monotonic() - began
    assert hashlib.sha256(x.db.read_bytes()).hexdigest() == original_hash
    assert Store(restored).export_state(include_files=True) == after
    assert AccessAudit(restored).export() == AccessAudit(x.db).export()
    x.db = restored
    x.start(ttl=1)
    x.login('analyst')
    time.sleep(1.1)
    x.request('analyst', '/api/state', expected=401, phase='session')
    x.login('operator')
    cookie = x.cookies['operator']
    x.request('operator', '/api/logout', {}, phase='session')
    x.request(None, '/api/state', cookie=cookie, expected=401, phase='session')
    x.stop()
    # Account revocation requires restart in this local implementation.
    config = json.loads(x.users.read_text())
    next(user for user in config['users'] if user['id'] == 'analyst')['active'] = False
    x.users.write_text(json.dumps(config))
    x.start()
    x.request('analyst', '/api/login', {'username': 'analyst', 'password': x.passwords['analyst']}, expected=401, phase='session')
    x.login('auditor')
    exported = x.request('auditor', '/api/audit/export', phase='recovery')
    assert verify_export(exported)
    accesses = x.request('auditor', '/api/access-audit/export', phase='recovery')
    assert verify_package(accesses)
    return {'acknowledged_snapshot_preserved_after_kill': True, 'sessions_revoked_on_restart': True,
            'session_expiry': True, 'logout_revocation': True, 'disabled_account_after_restart': True,
            'backup_restore_exact': True, 'source_unchanged_by_copy': True,
            'business_export_valid': True, 'access_export_valid': True,
            'restart_seconds': restart_seconds, 'backup_and_restore_seconds': restore_seconds,
            'precrash_access_events': len(ledger_before['events']), 'restored_access_events': len(accesses['events'])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--duration', type=float, default=60)
    parser.add_argument('--output', type=Path, default=ROOT / 'output/validation/trl-operation.json')
    args = parser.parse_args()
    if not math.isfinite(args.duration) or not 1 <= args.duration <= 120:
        parser.error('duration must be between 1 and 120 seconds; below60 is smoke only')
    report = {'date': datetime.now(timezone.utc).isoformat(),
        'scope': 'Local authenticated synthetic mixed HTTP; automatic clients are not human participants',
        'criteria_before_execution': {'read_p95_seconds_less_than': 2, 'unexpected_errors': 0,
            'expected_denials_conflicts_separate': True, 'business_and_access_audit_valid': True,
            'acknowledged_state_preserved_after_restart': True, 'backup_restore_exact': True},
        'limits': ['Fixture plus30 synthetic contracts, then one additional every10workcycles; not maximum volume',
            'Three reader clients and one serialized writer workflow', 'No real model/OCR load; local synthesis and TXT literal extraction',
            'No SSO/MFA/TLS/cloud; local accounts', 'SIGKILL after quiescent acknowledged work, not mid-commit durability proof',
            'Closed-loop clients; no fixed offered-rate saturation claim', 'Backup excludes credentials/session configuration',
            'Session expiry uses real monotonic clock with accelerated1s TTL only in test launcher',
            'No claim of CAIXA representativeness or TRL5 certification'],
        'smoke_only': args.duration < 60,
        'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((ROOT/'backend').glob('*.py'))}}
    report['source_sha256'].update({str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (Path(__file__), ROOT/'scripts/trl-operation-server.py')})
    with tempfile.TemporaryDirectory(prefix='elo-trl-operation-') as folder:
        x = Exercise(folder)
        try:
            x.start()
            case_id = journey(x)
            report['mixed'] = mixed(x, case_id, args.duration)
            report['recovery'] = recovery(x)
            state = Store(x.db).export_state(include_files=True)
            with sqlite3.connect(x.db) as connection:
                report['sqlite_integrity'] = connection.execute('PRAGMA integrity_check').fetchone()[0]
            final_access = AccessAudit(x.db).export()
            assert len(final_access['events']) == len(x.records), 'Every API response must have one access record'
            assert all(item['status'] == 'completed' for item in state['work_items'])
            assert len(state['work_items']) == report['mixed']['completed_work_cycles']
            assert state['actions'][0]['status'] == 'done'
            assert state['reports'][0]['status'] == 'approved'
            report['final_state'] = {'access_events': len(final_access['events']), 'access_count_exact': True,
                'completed_work_count_exact': True, 'action_closed': True, 'report_approved': True,
                'contracts': len(state['dataset']['contracts']), 'cases': len(state['cases']),
                'work_items': len(state['work_items']), 'attachments': len(state['attachments']),
                'reports': len(state['reports']), 'business_events': len(state['audit']),
                'audit_valid': state['audit_valid'], 'access_valid': verify_package(AccessAudit(x.db).export())}
        except Exception as error:
            report['failure_type'] = type(error).__name__
            report['failure'] = str(error) if isinstance(error, AssertionError) else 'See failed request metadata; no response body or secret persisted'
        finally:
            x.close()
        report['requests'] = x.records
    measured = [r for r in report['requests'] if r['phase'] == 'mixed']
    reads = [r['seconds'] for r in measured if r['method'] == 'GET']
    writes = [r['seconds'] for r in measured if r['method'] == 'POST' and r['expected_status'] == 200]
    report['metrics'] = {'mixed_requests': len(measured), 'read_p50_seconds': percentile(reads,.5),
        'read_p95_seconds': percentile(reads,.95), 'read_p99_seconds': percentile(reads,.99),
        'write_p95_seconds': percentile(writes,.95),
        'expected_negative_responses': sum(r['expected_status'] != 200 and r['status'] == r['expected_status'] for r in report['requests']),
        'unexpected_errors': sum(r['error_type'] is not None for r in report['requests'])}
    report['passed'] = 'failure_type' not in report and bool(reads) and percentile(reads,.95) < 2 and report['metrics']['unexpected_errors'] == 0 and report['sqlite_integrity'] == 'ok' and report['final_state']['audit_valid'] and report['final_state']['access_valid']
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({key: report[key] for key in ('passed','smoke_only','metrics')},ensure_ascii=False))
    if 'failure' in report:
        print(report['failure'])
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
