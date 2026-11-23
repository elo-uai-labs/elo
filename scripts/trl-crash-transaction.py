"""Disposable fault injection: kill after audit INSERT, before workflow UPDATE/COMMIT."""
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'backend'))
from domain import Store, serialize

PAYLOAD = {'actor': 'synthetic-crash-test', 'title': 'Trabalho de recuperação sintético',
           'description': 'Teste local de rollback com processo interrompido.', 'owner': 'synthetic-operator',
           'due': '2030-12-31', 'priority': 'normal', 'priority_reason': 'Ensaio controlado.',
           'case_ids': [], 'reason': 'Validar atomicidade.'}


def worker(db_path, marker):
    class PausedStore(Store):
        def connect(self):
            db = super().connect()
            def pause():
                marker.write_text('audit-inserted-before-workflow-update')
                time.sleep(30)
                return 1
            db.create_function('test_pause', 0, pause)
            return db
    PausedStore(db_path).apply('work/create', PAYLOAD)


def main():
    if len(sys.argv) == 4 and sys.argv[1] == '--worker':
        worker(Path(sys.argv[2]), Path(sys.argv[3]))
        return
    if len(sys.argv) != 1:
        raise SystemExit('Este ensaio cria seu próprio banco temporário; não aceita banco externo.')
    with tempfile.TemporaryDirectory(prefix='elo-transaction-crash-') as directory:
        db_path, marker = Path(directory)/'test.sqlite3', Path(directory)/'pause'
        store = Store(db_path)
        before = store.export_state(include_files=True)
        with sqlite3.connect(db_path) as db:
            db.execute('CREATE TRIGGER test_pause_before_update BEFORE UPDATE ON workflow BEGIN SELECT test_pause(); END')
        child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--worker', str(db_path), str(marker)],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic()+10
            while not marker.exists() and child.poll() is None and time.monotonic() < deadline:
                time.sleep(.02)
            assert marker.exists() and child.poll() is None, 'Worker must pause inside the write transaction'
            child.kill()
            child.wait(timeout=5)
        finally:
            if child.poll() is None:
                child.kill(); child.wait(timeout=5)
        recovered = Store(db_path).export_state(include_files=True)
        assert recovered == before, 'Uncommitted audit and workflow must both be absent'
        with sqlite3.connect(db_path) as db:
            integrity = db.execute('PRAGMA integrity_check').fetchone()[0]
            assert integrity == 'ok'
            db.execute('DROP TRIGGER test_pause_before_update')
        state = Store(db_path).apply('work/create', PAYLOAD)
        assert len(state['work_items']) == 1 and len(state['audit']) == len(before['audit'])+1 and state['audit_valid']
        report = {'scope': 'Synthetic disposable SQLite; SIGKILL paused inside transaction, not power/disk failure',
                  'criteria_before_execution': ['paused after audit INSERT and before workflow UPDATE', 'no uncommitted business/audit survives', 'retry commits exactly once', 'SQLite integrity ok'],
                  'passed': True, 'rollback_preserved_snapshot': True, 'retry_work_items': len(state['work_items']),
                  'retry_added_events': 1, 'sqlite_integrity': integrity,
                  'before_snapshot_sha256': hashlib.sha256(serialize(before).encode()).hexdigest(),
                  'recovered_snapshot_sha256': hashlib.sha256(serialize(recovered).encode()).hexdigest(),
                  'source_sha256': {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['backend/domain.py', 'scripts/trl-crash-transaction.py']},
                  'limits': ['Controlled SQLite trigger only in disposable database', 'Not HTTP receipt atomicity', 'No system power loss, file-system corruption, or production RPO guarantee']}
    destination = ROOT/'output/validation/trl5/crash-transaction.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
