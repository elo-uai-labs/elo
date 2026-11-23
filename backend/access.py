"""Optional local identities for synthetic testing; not a corporate identity provider."""

import argparse
import base64
import getpass
import hashlib
import hmac
import json
import os
import re
import secrets
import stat
import tempfile
import threading
import time
from copy import deepcopy
from pathlib import Path

from domain import WorkflowError

ITERATIONS = 600_000
ROLES = frozenset({'admin', 'analyst', 'reviewer', 'operator', 'auditor'})
READS = frozenset({'read', 'state', 'audit/export', 'supervision', 'laboratory', 'people', 'session', 'evidence/download', 'assistant/query'})
ANALYST = frozenset({'import', 'detect', 'dossier', 'decision', 'case/link', 'action', 'report/create'})
REVIEWER = frozenset({'risk/save', 'control/save', 'dimension/save', 'catalog/archive',
                      'maturity/assess', 'impact', 'action/edit', 'action/close', 'report/review', 'rule/config'})
MAX_SESSIONS = 1024
MAX_FAILURE_KEYS = 1024


def password_record(password):
    if not isinstance(password, str) or not 12 <= len(password) <= 1024:
        raise ValueError('Use uma senha entre 12 e 1024 caracteres.')
    salt = secrets.token_bytes(32)
    derived = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, ITERATIONS)
    return {'algorithm': 'pbkdf2-sha256', 'iterations': ITERATIONS,
            'salt': base64.b64encode(salt).decode('ascii'),
            'digest': base64.b64encode(derived).decode('ascii')}


def validate_config(config):
    try:
        if config['version'] != 1 or isinstance(config['version'], bool):
            raise ValueError
        users = config['users']
        if not isinstance(users, list) or not 1 <= len(users) <= 200:
            raise ValueError
        checked = {}
        for entry in users:
            identifier, name, roles = entry['id'], entry['name'], entry['roles']
            if not isinstance(identifier, str) or not re.fullmatch(r'[a-z0-9][a-z0-9._-]{0,63}', identifier) or identifier in checked:
                raise ValueError
            if not isinstance(name, str) or not name.strip() or len(name) > 80 or not isinstance(entry['active'], bool):
                raise ValueError
            if not isinstance(roles, list) or not roles or any(not isinstance(role, str) or role not in ROLES for role in roles) or len(set(roles)) != len(roles):
                raise ValueError
            record = entry['password']
            if record['algorithm'] != 'pbkdf2-sha256' or type(record['iterations']) is not int or record['iterations'] != ITERATIONS:
                raise ValueError
            salt = base64.b64decode(record['salt'], validate=True)
            derived = base64.b64decode(record['digest'], validate=True)
            if not 16 <= len(salt) <= 64 or len(derived) != 32:
                raise ValueError
            checked[identifier] = {'id': identifier, 'name': name.strip(), 'roles': sorted(roles),
                                   'active': entry['active'], 'salt': salt, 'digest': derived}
        return checked
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError('Configuração de identidades locais inválida.') from error


def read_config(path):
    path = Path(path)
    if path.is_symlink():
        raise ValueError('O arquivo de identidades não pode ser um link simbólico.')
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > 262144:
        raise ValueError('Arquivo de identidades inválido ou maior que 256 KiB.')
    if os.name == 'posix' and stat.S_IMODE(info.st_mode) & 0o077:
        raise ValueError('Restrinja o arquivo de identidades ao proprietário (chmod 600).')
    config = json.loads(path.read_text(encoding='utf-8'))
    validate_config(config)
    return config


class AccessService:
    def __init__(self, path, clock=time.monotonic, session_ttl=3600):
        if not isinstance(session_ttl, (int, float)) or not 0 < session_ttl <= 86400:
            raise ValueError('Duração de sessão inválida.')
        self._users = validate_config(read_config(path))
        self._clock, self.session_ttl = clock, session_ttl
        self._lock = threading.Lock()
        self._sessions, self._failures = {}, {}
        self._dummy_salt = secrets.token_bytes(32)
        self._dummy_digest = secrets.token_bytes(32)

    @classmethod
    def from_environment(cls):
        path = os.getenv('ELO_AUTH_USERS_FILE')
        return cls(path) if path else None

    @staticmethod
    def _public(user):
        return {key: deepcopy(user[key]) for key in ('id', 'name', 'roles')}

    def people(self):
        return [self._public(user) for user in self._users.values() if user['active']]

    def _purge(self, now):
        self._sessions = {key: value for key, value in self._sessions.items() if value['expires'] > now}
        self._failures = {key: [at for at in times if now - at < 60]
                          for key, times in self._failures.items() if times and now - times[-1] < 60}

    def authenticate(self, username, password):
        """Verify credentials with the same bounded attempt tracking as login."""
        if not isinstance(username, str) or not isinstance(password, str) or len(username) > 64 or len(password) > 1024:
            raise WorkflowError('Credenciais inválidas.', 401)
        username = username.strip().lower()
        with self._lock:
            now = self._clock()
            self._purge(now)
            failures = self._failures.get(username, [])
            if len(failures) >= 5:
                raise WorkflowError('Limite de tentativas atingido. Aguarde um minuto.', 429)
            if username not in self._failures and len(self._failures) >= MAX_FAILURE_KEYS:
                # Do not evict a locked identity: flooding unknown IDs must not reset its limit.
                raise WorkflowError('Limite local de tentativas atingido. Aguarde um minuto.', 429)
            user = self._users.get(username)
            candidate = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'),
                user['salt'] if user else self._dummy_salt, ITERATIONS)
            valid = hmac.compare_digest(candidate, user['digest'] if user else self._dummy_digest)
            if not valid or not user or not user['active']:
                self._failures[username] = [*failures, now]
                raise WorkflowError('Credenciais inválidas.', 401)
            self._failures.pop(username, None)
            return self._public(user)

    def login(self, username, password):
        user = self.authenticate(username, password)
        with self._lock:
            now = self._clock()
            self._purge(now)
            if len(self._sessions) >= MAX_SESSIONS:
                raise WorkflowError('Limite local de sessões atingido.', 429)
            token = secrets.token_urlsafe(32)
            key = hashlib.sha256(token.encode('ascii')).hexdigest()
            self._sessions[key] = {'id': user['id'], 'expires': now + self.session_ttl}
            return token, user

    def session(self, token):
        if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', token):
            return None
        key = hashlib.sha256(token.encode('ascii')).hexdigest()
        with self._lock:
            self._purge(self._clock())
            session = self._sessions.get(key)
            user = self._users.get(session['id']) if session else None
            return self._public(user) if user and user['active'] else None

    def logout(self, token):
        if isinstance(token, str) and len(token) <= 128:
            key = hashlib.sha256(token.encode('utf-8')).hexdigest()
            with self._lock:
                self._sessions.pop(key, None)

    def validate_owner(self, owner_id):
        owner = self._users.get(owner_id) if isinstance(owner_id, str) else None
        if not owner or not owner['active'] or not set(owner['roles']) & {'operator', 'analyst', 'admin'}:
            raise WorkflowError('Escolha um responsável ativo com perfil de execução.', 422)
        return self._public(owner)

    def authorize(self, user, command, state=None, data=None):
        stored = self._users.get(user.get('id')) if isinstance(user, dict) else None
        if not stored or not stored['active']:
            raise WorkflowError('Entre para continuar.', 401)
        roles = set(stored['roles'])
        data = data or {}
        if command in READS:
            return
        if command == 'access-audit/export':
            if not roles & {'reviewer', 'auditor', 'admin'}:
                raise WorkflowError('Seu perfil não permite exportar registros de acesso.', 403)
            return
        if command in {'evidence/analyze', 'evidence/review'}:
            if not roles & {'analyst', 'reviewer', 'admin'}:
                raise WorkflowError('Seu perfil não permite analisar ou revisar documentos.', 403)
            return
        if command in {'work/create', 'work/update'}:
            if not roles & {'analyst', 'reviewer', 'admin'}:
                raise WorkflowError('Seu perfil não permite gerenciar trabalhos da segunda linha.', 403)
            self.validate_owner(data.get('owner'))
            return
        if command == 'work/status':
            item = next((row for row in (state or {}).get('work_items', []) if row['id'] == data.get('id')), None)
            if item is None:
                raise WorkflowError('Trabalho não encontrado.', 403)
            if data.get('status') == 'cancelled':
                if not roles & {'analyst', 'reviewer', 'admin'}:
                    raise WorkflowError('Seu perfil não permite cancelar este trabalho.', 403)
            elif not roles & {'operator', 'analyst', 'admin'} or item['owner'] != stored['id']:
                raise WorkflowError('Somente o executor atribuído pode iniciar ou concluir este trabalho.', 403)
            return
        if command == 'scenario/create':
            if not roles & {'analyst', 'reviewer', 'admin'}:
                raise WorkflowError('Seu perfil não permite criar uma simulação.', 403)
            return
        if command == 'evidence/upload':
            action_id = data.get('action_id')
            if action_id is None:
                if not roles & {'analyst', 'reviewer', 'admin'}:
                    raise WorkflowError('Seu perfil não permite anexar evidência ao caso.', 403)
            else:
                action = next((item for item in (state or {}).get('actions', []) if item['id'] == action_id), None)
                if (not roles & {'operator', 'analyst', 'admin'} or not action
                        or action['owner'] != stored['id'] or action['case_id'] != data.get('case_id')
                        or action['status'] in {'done', 'closure_requested'}):
                    raise WorkflowError('Somente o executor atribuído pode anexar evidência a este plano aberto.', 403)
            return
        allowed = ((command in ANALYST and bool(roles & {'analyst', 'admin'}))
                   or (command in REVIEWER and bool(roles & {'reviewer', 'admin'}))
                   or (command == 'action/update' and bool(roles & {'operator', 'analyst', 'admin'})))
        if not allowed:
            raise WorkflowError('Seu perfil não permite esta ação.', 403)
        if command == 'report/review':
            report = next((item for item in (state or {}).get('reports', []) if item['id'] == data.get('id')), None)
            if not report or report['creator'] == stored['id']:
                raise WorkflowError('O relatório exige revisor diferente de quem criou o rascunho.', 403)
        if command in {'action', 'action/edit'}:
            self.validate_owner(data.get('owner'))
        if command == 'impact':
            snapshot = state or {}
            cases = snapshot.get('cases', [snapshot['case']] if snapshot.get('case') else [])
            identifier = data.get('case_id')
            case = next((item for item in cases if item['id'] == identifier), None) if identifier is not None else (cases[0] if cases else None)
            if not case or not case.get('decision'):
                raise WorkflowError('O caso precisa de uma decisão humana antes da revisão do impacto.', 403)
            if case['decision'].get('actor') == stored['id']:
                raise WorkflowError('O impacto exige revisor diferente de quem qualificou o caso.', 403)
        if command in {'action/update', 'action/close'}:
            action = next((item for item in (state or {}).get('actions', []) if item['id'] == data.get('id')), None)
            if not action:
                raise WorkflowError('Plano não encontrado.', 403)
            if command == 'action/update' and action['owner'] != stored['id']:
                raise WorkflowError('Somente o responsável atribuído pode registrar a execução.', 403)
            if command == 'action/close' and action.get('closure_request', {}).get('actor') == stored['id']:
                raise WorkflowError('O encerramento exige outro revisor.', 403)


def provision(path, identifier, name, roles, password):
    """Offline setup only. No default accounts and no secret output."""
    path = Path(path)
    if path.is_symlink():
        raise ValueError('O arquivo de identidades não pode ser um link simbólico.')
    config = read_config(path) if path.exists() else {'version': 1, 'users': []}
    if any(user['id'] == identifier for user in config['users']):
        raise ValueError('O identificador já existe; nenhuma conta foi alterada.')
    config['users'].append({'id': identifier, 'name': name, 'roles': roles, 'active': True,
                            'password': password_record(password)})
    validate_config(config)
    # Provision while the server is stopped. Replacing the file revokes sessions on restart.
    descriptor, temporary = tempfile.mkstemp(prefix='.elo-users-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as target:
            json.dump(config, target, ensure_ascii=False, indent=2)
            target.write('\n')
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    create = commands.add_parser('provision', help='Adiciona uma identidade local explicitamente; servidor deve estar parado.')
    create.add_argument('--file', type=Path, required=True)
    create.add_argument('--id', required=True)
    create.add_argument('--name', required=True)
    create.add_argument('--roles', nargs='+', choices=sorted(ROLES), required=True)
    args = parser.parse_args()
    try:
        password = getpass.getpass('Senha local (mínimo 12 caracteres): ')
        if password != getpass.getpass('Repita a senha: '):
            raise ValueError('As senhas não coincidem.')
        provision(args.file, args.id, args.name, args.roles, password)
        print('Identidade local criada. Reinicie o servidor para carregar a configuração.')
    except (OSError, ValueError, EOFError) as error:
        parser.exit(1, f'Configuração não concluída: {error}\n')


if __name__ == '__main__':
    main()
