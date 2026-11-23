#!/usr/bin/env python3
"""Bounded loopback HTTP load; exclusively disposable synthetic databases."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from urllib.request import urlopen
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from domain import Store
from rule_config import get_config
from access_audit import AccessAudit, verify_package


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def percentile(values, fraction):
    return sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)] if values else None


def seed(store, target):
    existing = len(store.export_state()['dataset']['contracts'])
    for first in range(existing, target, 500):
        contracts = [{'id': f'CTR-CAP-{i:04}', 'supplier_id': 'FOR-031',
                      'approver_id': 'EMP-014', 'title': f'Contrato sintético de carga {i}'}
                     for i in range(first, min(first + 500, target))]
        store.apply('import', {'actor': 'capacity-test', 'synthetic': True,
                              'dataset': {'employees': [], 'suppliers': [], 'contracts': contracts}})
    store.apply('detect', {'actor': 'capacity-test'})


def run(args):
    report = {'date': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'scope': 'Synthetic loopback HTTP GET /api/state with real access-ledger writes; no model calls',
              'harness_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'environment': {'python': platform.python_version(), 'platform': platform.platform()},
              'criteria_declared_before_execution': {'p95_seconds_less_than': 2, 'errors': 0,
                  'business_state_unchanged_by_reads': True, 'access_chain_valid': True},
              'limits': ['No production capacity certification', 'No browser rendering or authenticated sessions',
                         'No model, OCR or attachment load', 'Business history uses synthetic configuration changes, not real analyst activity',
                         'Closed-loop clients with 50ms pause; not fixed-rate offered load'],
              'code_sha256': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                              for path in sorted((ROOT / 'backend').glob('*.py'))}, 'scenarios': []}
    with tempfile.TemporaryDirectory(prefix='elo-capacity-') as folder:
        db = Path(folder) / 'capacity.sqlite3'
        store = Store(db)
        seed(store, 200)
        ledger = AccessAudit(db)
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]
        url = f'http://127.0.0.1:{port}'
        env = dict(os.environ, ELO_ENV='test', ELO_REQUIRE_AUTH='0', ELO_AUTH_USERS_FILE='',
                   ELO_AI_PROVIDER='openai', OPENAI_API_KEY='', ELO_ON_DEVICE_BIN='')
        with open(Path(folder) / 'server.log', 'wb') as log:
            server = subprocess.Popen([sys.executable, str(ROOT / 'scripts/capacity-server.py'), '--port', str(port), '--db', str(db)],
                                      cwd=ROOT, env=env, stdout=log, stderr=log)
            try:
                for _ in range(100):
                    if server.poll() is not None:
                        raise RuntimeError('Isolated server exited before readiness')
                    try:
                        with urlopen(url + '/health', timeout=1) as response:
                            if response.status == 200:
                                break
                    except OSError:
                        time.sleep(.1)
                else:
                    raise RuntimeError('Isolated server readiness timeout')
                scenarios = [('small-c1', 200, 1, 10), ('small-c4', 200, 4, 15),
                             ('history-c4', 200, 4, 20), ('large-c4', 2000, 4, 60),
                             ('large-spike-c8', 2000, 8, 15)]
                for name, contracts, concurrency, duration in scenarios:
                    if name == 'history-c4':
                        for _ in range(250):
                            config = get_config(store.export_state(), 'contact-code-match')
                            store.apply('rule/config', {**config, 'actor': 'capacity-test',
                                'reason': 'Revisão sintética para ensaio de histórico crescente'})
                    if len(store.export_state()['dataset']['contracts']) != contracts:
                        seed(store, contracts)
                    before = store.export_state()
                    access_before = len(ledger.export()['events'])
                    stop = threading.Event()
                    rss = []
                    def sample_memory():
                        while not stop.is_set():
                            try:
                                rss.append(int(subprocess.check_output(['ps', '-o', 'rss=', '-p', str(server.pid)], text=True).strip()))
                            except (ValueError, subprocess.SubprocessError):
                                pass
                            stop.wait(.5)
                    sampler = threading.Thread(target=sample_memory, daemon=True)
                    sampler.start()
                    start = time.monotonic()
                    deadline = start + duration * args.duration_scale
                    def worker():
                        records = []
                        while time.monotonic() < deadline:
                            began = time.monotonic()
                            error, size = None, 0
                            try:
                                with urlopen(url + '/api/state', timeout=15) as response:
                                    raw = response.read()
                                    size = len(raw)
                                    payload = json.loads(raw)
                                    if response.status != 200 or payload.get('audit_valid') is not True:
                                        error = 'invalid-status-or-business-audit'
                            except HTTPError as exc:
                                error = f'HTTP-{exc.code}'
                                exc.close()
                            except Exception as exc:
                                error = type(exc).__name__  # Never copy response bodies/credentials.
                            records.append((time.monotonic() - began, error, size, began - start))
                            time.sleep(.05)
                        return records
                    try:
                        with ThreadPoolExecutor(max_workers=concurrency) as pool:
                            records = sum(list(pool.map(lambda _: worker(), range(concurrency))), [])
                    finally:
                        stop.set()
                        sampler.join()
                    elapsed = time.monotonic() - start
                    after = store.export_state()
                    access = ledger.export()
                    values = [row[0] for row in records]
                    errors = [row[1] for row in records if row[1]]
                    buckets = []
                    for index in range(3):
                        selected = [row[0] for row in records if index * duration * args.duration_scale / 3 <= row[3] < (index+1) * duration * args.duration_scale / 3]
                        buckets.append({'third': index+1, 'requests': len(selected), 'p95_seconds': percentile(selected, .95)})
                    result = {'name': name, 'contracts': contracts, 'cases': len(after['cases']),
                              'business_events': len(after['audit']), 'concurrency': concurrency,
                              'scheduled_seconds': duration * args.duration_scale, 'elapsed_seconds': elapsed,
                              'requests': len(records), 'throughput_rps': len(records) / elapsed,
                              'errors': len(errors), 'error_types': sorted(set(errors)),
                              'p50_seconds': percentile(values, .5), 'p95_seconds': percentile(values, .95),
                              'p99_seconds': percentile(values, .99), 'max_seconds': max(values, default=None),
                              'time_thirds': buckets, 'rss_peak_kib': max(rss, default=None),
                              'response_bytes_max': max((r[2] for r in records), default=0),
                              'access_events_before': access_before, 'access_events_after': len(access['events']),
                              'access_chain_valid': verify_package(access),
                              'access_event_count_exact': len(access['events']) - access_before == len(records),
                              'business_state_unchanged': digest(before) == digest(after),
                              'business_audit_valid': after['audit_valid']}
                    result['passed'] = bool(values) and result['p95_seconds'] < 2 and not errors and all(result[key] for key in (
                        'access_chain_valid', 'access_event_count_exact', 'business_state_unchanged', 'business_audit_valid'))
                    report['scenarios'].append(result)
                    print(json.dumps(result), flush=True)
                with sqlite3.connect(db) as connection:
                    report['sqlite_integrity_check'] = connection.execute('PRAGMA integrity_check').fetchone()[0]
            finally:
                server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()
        report['ledger_failure_diagnostics'] = [json.loads(line.split(' ', 1)[1])
            for line in (Path(folder) / 'server.log').read_text().splitlines()
            if line.startswith('CAPACITY_LEDGER_FAILURE ')]
    report['first_observed_threshold_failure'] = next((s['name'] for s in report['scenarios'] if not s['passed']), None)
    report['passed'] = all(s['passed'] for s in report['scenarios']) and report['sqlite_integrity_check'] == 'ok'
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'output/validation/capacity-local.json')
    parser.add_argument('--duration-scale', type=float, default=1, help='Default 120s scheduled load; <1 is smoke only.')
    options = parser.parse_args()
    if not 0.01 <= options.duration_scale <= 3:
        parser.error('duration-scale must be between 0.01 and 3')
    raise SystemExit(run(options))
