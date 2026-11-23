"""Independent local HTTP-access ledger; never changes business snapshots."""
import hashlib
import ipaddress
import json
import re
import sqlite3
from contextlib import closing
from datetime import datetime, timezone

FORMAT = 'elo-access-audit-v1'
EVENTS = frozenset({'read', 'login', 'logout', 'export', 'download', 'denial', 'write'})
MODES = frozenset({'local-auth', 'local-demo', 'local-service', 'anonymous'})
OUTCOMES = frozenset({'success', 'denied', 'error'})
FIELDS = {'seq', 'timestamp', 'actor', 'mode', 'event', 'target', 'outcome', 'ip', 'previous_hash'}


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def validate_event(event):
    if not isinstance(event, dict) or set(event) != FIELDS:
        raise ValueError('Campos inválidos na trilha de acesso.')
    if type(event['seq']) is not int or event['seq'] < 1:
        raise ValueError('Sequência inválida.')
    if not isinstance(event['actor'], str) or not re.fullmatch(r'[A-Za-z0-9._:-]{1,80}', event['actor']):
        raise ValueError('Use identidade canônica, sem conteúdo da requisição.')
    if event['mode'] not in MODES or event['event'] not in EVENTS or event['outcome'] not in OUTCOMES:
        raise ValueError('Tipo de evento inválido.')
    if not isinstance(event['target'], str) or not re.fullmatch(r'/[A-Za-z0-9/_-]{0,159}', event['target']):
        raise ValueError('Use apenas rota normalizada, sem query ou corpo.')
    if not isinstance(event['ip'], str) or len(event['ip']) > 45:
        raise ValueError('Endereço de origem inválido.')
    ipaddress.ip_address(event['ip'])
    timestamp = event['timestamp']
    if not isinstance(timestamp, str) or len(timestamp) > 40 or datetime.fromisoformat(timestamp).utcoffset() is None:
        raise ValueError('Data/hora precisa de fuso explícito.')
    if not isinstance(event['previous_hash'], str) or (event['previous_hash'] and not re.fullmatch(r'[0-9a-f]{64}', event['previous_hash'])):
        raise ValueError('Hash anterior inválido.')


def checked_events(db):
    events, previous = [], ''
    for expected, (seq, encoded, stored_hash) in enumerate(db.execute('SELECT seq,event,hash FROM access_audit ORDER BY seq'), 1):
        event = json.loads(encoded)
        validate_event(event)
        if seq != expected or event['seq'] != expected or event['previous_hash'] != previous or digest(event) != stored_hash:
            raise ValueError('Integridade da trilha de acesso inválida.')
        events.append({**event, 'hash': stored_hash})
        previous = stored_hash
    return events


def verify_database(db):
    """Read-only verifier. Missing table denotes legacy, not audited historical access."""
    try:
        exists = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='access_audit'").fetchone()
        if exists:
            checked_events(db)
        return True
    except (sqlite3.Error, ValueError, TypeError, KeyError, OverflowError):
        return False


def package_for(events):
    return {'format': FORMAT, 'events': events, 'manifest': {
        'count': len(events), 'head_hash': events[-1]['hash'] if events else '',
        'events_sha256': digest(events)}}


def verify_package(package):
    try:
        if not isinstance(package, dict) or set(package) != {'format', 'events', 'manifest'} or package['format'] != FORMAT:
            return False
        events = package['events']
        if not isinstance(events, list):
            return False
        previous = ''
        for seq, row in enumerate(events, 1):
            if not isinstance(row, dict) or set(row) != FIELDS | {'hash'}:
                return False
            event = {key: row[key] for key in FIELDS}
            validate_event(event)
            if event['seq'] != seq or event['previous_hash'] != previous or digest(event) != row['hash']:
                return False
            previous = row['hash']
        return canonical(package['manifest']) == canonical(package_for(events)['manifest'])
    except (ValueError, TypeError, KeyError, OverflowError):
        return False


class AccessAudit:
    def __init__(self, path):
        self.path = path
        with closing(sqlite3.connect(path, timeout=5)) as db, db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS access_audit(seq INTEGER PRIMARY KEY, event TEXT NOT NULL, hash TEXT NOT NULL);
                CREATE TRIGGER IF NOT EXISTS access_audit_no_update BEFORE UPDATE ON access_audit
                  BEGIN SELECT RAISE(ABORT, 'append-only'); END;
                CREATE TRIGGER IF NOT EXISTS access_audit_no_delete BEFORE DELETE ON access_audit
                  BEGIN SELECT RAISE(ABORT, 'append-only'); END;
            ''')

    def append(self, *, actor, mode, event, target, outcome, ip):
        with closing(sqlite3.connect(self.path, timeout=5)) as db, db:
            db.execute('BEGIN IMMEDIATE')
            events = checked_events(db)
            row = {'seq': len(events) + 1, 'timestamp': datetime.now(timezone.utc).isoformat(timespec='milliseconds'),
                   'actor': actor, 'mode': mode, 'event': event, 'target': target, 'outcome': outcome, 'ip': ip,
                   'previous_hash': events[-1]['hash'] if events else ''}
            validate_event(row)
            hashed = digest(row)
            db.execute('INSERT INTO access_audit VALUES (?,?,?)', (row['seq'], canonical(row), hashed))
            return {**row, 'hash': hashed}

    def export(self):
        with closing(sqlite3.connect(self.path, timeout=5)) as db:
            db.execute('BEGIN')
            return package_for(checked_events(db))
