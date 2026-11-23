"""Explicitly invoked, local synthetic inbox connector. No network or default job."""

import argparse
import hashlib
import json
import os
import re
import sqlite3
import stat
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from domain import Store, WorkflowError, required, require, serialize

MAX_FILE_BYTES = 512 * 1024
MAX_FILES_PER_PASS = 100
MAX_BATCHES = 2000


def source_slug(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,47}', value):
        raise WorkflowError('source_id precisa ser um slug de até 48 caracteres minúsculos.', 422)
    return value


def source_name(value):
    if (not isinstance(value, str) or not value or len(value) > 120 or not value.endswith('.json')
            or '/' in value or '\\' in value or any(ord(char) < 32 or ord(char) == 127 for char in value)):
        raise WorkflowError('Use um nome de arquivo JSON sem caminho ou caracteres de controle.', 422)
    return value


def batch_identity(data):
    identifier = source_slug(data.get('source_id'))
    name = source_name(data.get('source_name'))
    payload = data.get('payload')
    if not isinstance(payload, dict) or set(payload) != {'synthetic', 'dataset'} or payload['synthetic'] is not True:
        raise WorkflowError('A entrada precisa declarar synthetic: true e dataset.', 422)
    canonical = serialize(payload).encode('utf-8')
    if len(canonical) > MAX_FILE_BYTES:
        raise WorkflowError('O lote excede 512 KiB.', 413)
    return identifier, name, hashlib.sha256(canonical).hexdigest(), payload


def transition(state, data):
    """Stage the entire batch before publishing it into the supplied state."""
    from domain import transition as domain_transition

    source_id, name, content_hash, payload = batch_identity(data)
    prior = state.get('integration_batches', [])
    require(not any(batch['source_id'] == source_id and batch['content_sha256'] == content_hash for batch in prior),
            'Este lote sintético já foi processado por esta fonte.')
    require(len(prior) < MAX_BATCHES, 'Limite local de 2000 lotes de integração atingido.')
    working = deepcopy(state)
    actor = 'Conector sintético:' + source_id
    _, _, imported = domain_transition(working, 'import', {
        'actor': actor, 'synthetic': True, 'dataset': deepcopy(payload['dataset']),
    })
    case_ids, scanned, rules = [], [], []
    requested_rules = []
    if payload['dataset']['contracts']:
        requested_rules.append('contact-code-match')
    if payload['dataset']['suppliers'] or payload['dataset']['contracts']:
        requested_rules.append('supplier-shared-contact')
    for rule_id in requested_rules:
        processed = (working.get('detection') or {}).get('processed_by_rule', {}).get(rule_id, [])
        if not any(contract['id'] not in processed for contract in working['dataset']['contracts']):
            continue
        _, _, detected = domain_transition(working, 'detect', {'actor': actor, 'rule_id': rule_id})
        case_ids.extend(identifier for identifier in detected['case_ids'] if identifier not in case_ids)
        scanned.extend(identifier for identifier in detected['contracts_analyzed'] if identifier not in scanned)
        rules.append(deepcopy(detected['rule']))
    batch = {
        'id': f'BAT-{len(prior) + 1:04}', 'source_id': source_id, 'source_name': name,
        'content_sha256': content_hash, 'actor': actor,
        'at': datetime.now(timezone.utc).isoformat(timespec='milliseconds'),
        'synthetic': True, 'case_ids': list(case_ids), 'contracts_analyzed': list(scanned),
        'rules': rules,
        'imported_counts': imported['counts'], 'record_ids': imported['record_ids'],
    }
    working.setdefault('integration_batches', []).append(batch)
    state.clear()
    state.update(working)
    return 'Integração sintética executada', actor, deepcopy(batch)


def read_batch(path, source_id, directory_fd=None):
    """Open regular files without following a symlink and cap bytes before JSON."""
    path = Path(path)
    source_name(path.name)
    if directory_fd is None and path.is_symlink():
        raise WorkflowError('Links simbólicos não são aceitos na entrada.', 422)
    descriptor = os.open(path.name if directory_fd is not None else path,
                         os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0),
                         dir_fd=directory_fd)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            raise WorkflowError('A entrada precisa ser um arquivo regular.', 422)
        if not 0 < info.st_size <= MAX_FILE_BYTES:
            raise WorkflowError('O arquivo deve ter entre 1 byte e 512 KiB.', 413)
        with os.fdopen(descriptor, 'rb') as file:
            descriptor = None
            content = file.read(MAX_FILE_BYTES + 1)
        if len(content) > MAX_FILE_BYTES:
            raise WorkflowError('O arquivo excede 512 KiB.', 413)
        payload = json.loads(content.decode('utf-8'))
        data = {'source_id': source_slug(source_id), 'source_name': path.name, 'payload': payload}
        batch_identity(data)
        return data
    finally:
        if descriptor is not None:
            os.close(descriptor)


def run_once(store, inbox, source_id, emit=print):
    """Run one bounded pass; duplicates are no-ops, not new audit events."""
    source_id = source_slug(source_id)
    inbox = Path(inbox)
    if inbox.is_symlink() or not inbox.is_dir():
        raise WorkflowError('A pasta de entrada precisa ser um diretório local sem link simbólico.', 422)
    directory_fd = os.open(inbox, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        return _run_once_fd(store, directory_fd, source_id, emit)
    finally:
        os.close(directory_fd)


def _run_once_fd(store, directory_fd, source_id, emit):
    # Every child is opened relative to this same directory, even if its path is renamed.
    results = {'processed': 0, 'duplicate': 0, 'failed': 0}
    candidates = []
    with os.scandir(directory_fd) as entries:
        for entry in entries:
            if entry.name.endswith('.json'):
                if len(candidates) >= MAX_FILES_PER_PASS:
                    raise WorkflowError('A pasta excede 100 arquivos JSON; divida a entrada antes de executar.', 413)
                candidates.append(Path(entry.name))
    for path in sorted(candidates):
        name = None
        try:
            name = source_name(path.name)
            data = read_batch(path, source_id, directory_fd=directory_fd)
            _, _, content_hash, _ = batch_identity(data)
            snapshot = store.read()
            if not snapshot.get('audit_valid', False):
                raise WorkflowError('A integridade da trilha precisa ser verificada.', 409)
            if any(batch['source_id'] == source_id and batch['content_sha256'] == content_hash
                   for batch in snapshot.get('integration_batches', [])):
                results['duplicate'] += 1
                continue
            def trusted_service(state):
                return {'mode': 'local-service', 'service_id': source_id}
            try:
                state = store.apply('integration/import', data, authorize=trusted_service)
            except WorkflowError:
                # Another connector can win the same transaction after the precheck.
                latest = store.read()
                if latest.get('audit_valid') and any(batch['source_id'] == source_id and batch['content_sha256'] == content_hash
                                                     for batch in latest.get('integration_batches', [])):
                    results['duplicate'] += 1
                    continue
                raise
            batch = next(batch for batch in state['integration_batches']
                         if batch['source_id'] == source_id and batch['content_sha256'] == content_hash)
            results['processed'] += 1
            emit(json.dumps({'status': 'processed', 'source_id': source_id, 'source_name': name,
                             'batch_id': batch['id'], 'contracts_analyzed': len(batch['contracts_analyzed']),
                             'case_count': len(batch['case_ids'])}, ensure_ascii=False))
        except (OSError, sqlite3.Error, UnicodeError, ValueError, WorkflowError) as error:
            results['failed'] += 1
            emit(json.dumps({'status': 'failed', 'source_id': source_id, 'source_name': name,
                             'error': str(error) if isinstance(error, WorkflowError) else type(error).__name__}, ensure_ascii=False))
    return results


def run_loop(store, inbox, source_id, interval, emit=print, sleep=time.sleep):
    if not isinstance(interval, (int, float)) or not 10 <= interval <= 86400:
        raise ValueError('O intervalo deve estar entre 10 segundos e 24 horas.')
    failures = 0
    while True:
        try:
            result = run_once(store, inbox, source_id, emit=emit)
            failed = result['failed'] > 0
        except (OSError, sqlite3.Error, ValueError, WorkflowError) as error:
            failed = True
            emit(json.dumps({'status': 'pass-failed', 'error': str(error) if isinstance(error, WorkflowError) else type(error).__name__}))
        failures = min(failures + 1, 5) if failed else 0
        sleep(min(interval * (2 ** failures), max(interval, 300)))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inbox', type=Path, required=True)
    parser.add_argument('--db', type=Path, required=True, help='Banco escolhido explicitamente; nunca há banco padrão.')
    parser.add_argument('--source-id', required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--once', action='store_true')
    mode.add_argument('--interval', type=float, help='Monitoramento local enquanto o processo roda; mínimo 10 segundos.')
    args = parser.parse_args(argv)
    try:
        source_slug(args.source_id)
        if args.interval is not None and not 10 <= args.interval <= 86400:
            parser.error('--interval precisa estar entre 10 segundos e 24 horas.')
        if args.inbox.is_symlink() or not args.inbox.is_dir():
            parser.error('--inbox precisa ser um diretório local existente, sem link simbólico.')
        store = Store(args.db)
        if args.once:
            result = run_once(store, args.inbox, args.source_id)
            print(json.dumps({'status': 'complete', **result}))
            return 1 if result['failed'] else 0
        run_loop(store, args.inbox, args.source_id, args.interval)
        return 0
    except KeyboardInterrupt:
        print(json.dumps({'status': 'stopped'}))
        return 0
    except (OSError, sqlite3.Error, ValueError, WorkflowError) as error:
        print(json.dumps({'status': 'failed', 'error': str(error) if isinstance(error, WorkflowError) else type(error).__name__}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
