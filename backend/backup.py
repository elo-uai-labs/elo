"""Explicit, local SQLite backup/restore; never initializes the source."""
import argparse
import json
import os
import sqlite3
import stat
import tempfile
from contextlib import closing
from pathlib import Path

from domain import Store, WorkflowError
from access_audit import verify_database


def verified_copy(source, destination):
    source, destination = Path(source).absolute(), Path(destination).absolute()
    info = source.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_size == 0:
        raise ValueError('A origem precisa ser um banco Elo regular, não vazio e sem link simbólico.')
    if os.path.lexists(destination):
        raise FileExistsError('O destino já existe; escolha um caminho novo.')
    if not destination.parent.is_dir():
        raise ValueError('O diretório de destino precisa existir.')
    temporary = None
    try:
        # mode=ro prohibits source creation/writes; backup captures SQLite tables and BLOBs.
        with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)) as original:
            current = source.lstat()
            if not stat.S_ISREG(current.st_mode) or (current.st_dev, current.st_ino) != (info.st_dev, info.st_ino):
                raise ValueError('A origem mudou durante a abertura; tente novamente.')
            original.execute('PRAGMA query_only=ON')
            original.execute('BEGIN')
            tables = {row[0] for row in original.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not {'workflow', 'audit'} <= tables:
                raise ValueError('A origem não é um banco Elo.')
            rows = original.execute('SELECT id, value FROM workflow').fetchall()
            if len(rows) != 1 or rows[0][0] != 1:
                raise ValueError('Estado Elo ausente ou inválido.')
            raw = json.loads(rows[0][1])
            if not isinstance(raw, dict) or not {'dataset', 'case', 'risk', 'maturity', 'actions'} <= raw.keys():
                raise ValueError('Estado Elo inválido.')
            descriptor, temporary = tempfile.mkstemp(prefix='.elo-backup-', suffix='.sqlite3', dir=destination.parent)
            os.close(descriptor)
            with closing(sqlite3.connect(temporary)) as copy:
                original.backup(copy)
        with closing(sqlite3.connect(temporary)) as copy:
            if copy.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                raise ValueError('Integridade SQLite inválida.')
            if not verify_database(copy):
                raise ValueError('Integridade da trilha de acesso inválida.')
        # Compatibility migrations, if needed, affect this private copy only.
        snapshot = Store(temporary).export_state(include_files=True)
        if not snapshot['audit_valid']:
            raise ValueError('Integridade da trilha inválida.')
        with open(temporary, 'rb') as handle:
            os.fsync(handle.fileno())
        # link is atomic and fails if ANY destination already exists, including symlinks.
        os.link(temporary, destination)
        return {'status': 'verified', 'audit_events': len(snapshot['audit']),
                'attachments': len(snapshot.get('attachment_files', []))}
    finally:
        if temporary is not None:
            for suffix in ('', '-journal', '-wal', '-shm'):
                try:
                    os.unlink(temporary + suffix)
                except FileNotFoundError:
                    pass


def main(argv=None):
    parser = argparse.ArgumentParser(description='Cópia/restauração local verificada para um caminho novo.')
    parser.add_argument('operation', choices=('backup', 'restore'))
    parser.add_argument('--source', required=True)
    parser.add_argument('--destination', required=True)
    args = parser.parse_args(argv)
    try:
        result = verified_copy(args.source, args.destination)
    except (OSError, ValueError, sqlite3.Error, WorkflowError, KeyError, TypeError) as error:
        parser.exit(1, f'Falha na cópia verificada ({type(error).__name__}); nenhum destino existente foi substituído.\n')
    print(json.dumps({'operation': args.operation, **result}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
