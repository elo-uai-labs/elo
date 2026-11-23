"""Local Elo API and the compiled Porsche Design System application."""

import argparse
import base64
import hashlib
import json
import mimetypes
import os
import re
import sqlite3
from http.cookies import CookieError, SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from urllib.parse import parse_qs, unquote, urlsplit

import dossier
import governance
import reporting
import work
from access import AccessService
from access_audit import AccessAudit
from audit_export import build_export
from domain import Store, WorkflowError, choice, require, required

ROOT = Path(__file__).resolve().parent.parent
SESSION_COOKIE = "elo_session"
COMMANDS = {"import", "import/preview", "import/file", "detect", "dossier", "decision", "impact", "action", "action/update", "action/edit", "action/close", "evidence/upload", "scenario/create", "assistant/query", "evidence/analyze", "evidence/review", "rule/config", *governance.COMMANDS, *reporting.COMMANDS, *work.COMMANDS}


class EloServer(ThreadingHTTPServer):
    request_queue_size = 64
    daemon_threads = True

    def __init__(self, address, store, static_dir=None, frontend_port=None, access_service=...):
        self.access = AccessService.from_environment() if access_service is ... else access_service
        self.store = store
        self.access_audit = AccessAudit(store.path)
        self.static_dir = Path(static_dir).resolve() if static_dir else None
        self.frontend_port = frontend_port
        self.dossier_lock = Lock()
        self.document_lock = Lock()
        super().__init__(address, Handler)

    def summarize(self, mode, case_id=None, actor=None, authorize=None):
        require(self.dossier_lock.acquire(blocking=False), "Já existe uma síntese em andamento.")
        try:
            snapshot = self.store.read(case_id)
            require(snapshot["audit_valid"], "A integridade da trilha precisa ser verificada.")
            if authorize:
                authorize(snapshot)
            case = snapshot["case"]
            require(case and not case["decision"], "O caso precisa estar aguardando análise.")
            generated = {**dossier.generate(case["evidence"], mode, rule_id=case.get("rule", {}).get("id", "contact-code-match")), "case_id": case["id"]}
            if actor is not None:
                generated["actor"] = actor
            return self.store.apply("dossier", generated, authorize=authorize)
        finally:
            self.dossier_lock.release()


    def consult(self, data, authorize=None):
        import consultation
        actor = required(data, "actor", 80)
        require(self.dossier_lock.acquire(blocking=False), "Já existe uma síntese ou consulta em andamento.")
        try:
            snapshot = self.store.read(data.get("case_id"))
            if authorize:
                authorize(snapshot)
            context = consultation.prepare(snapshot, data)
            generated = consultation.answer(context)
            return self.store.apply("assistant/record", {"actor": actor, "case_id": context["case_id"], "answer": generated}, authorize=authorize)
        finally:
            self.dossier_lock.release()


    def analyze_document(self, data, authorize=None):
        import document_analysis
        actor = required(data, "actor", 80)
        snapshot = self.store.read()
        if authorize:
            authorize(snapshot)
        require(len(snapshot.get("document_analyses", [])) < 200, "Limite local de 200 análises atingido.")
        metadata, content = self.store.evidence_file(required(data, "attachment_id", 32))
        mode = data.get("mode", "literal")
        require(mode in ("literal", "ocr"), "Escolha extração literal ou OCR local.")
        require(not any(row["attachment_id"] == metadata["id"] and row.get("method", "literal") == mode for row in snapshot.get("document_analyses", [])), "Este arquivo já foi analisado por este método.")
        require(self.document_lock.acquire(blocking=False), "Já existe uma extração em andamento. Tente novamente após a conclusão.")
        try:
            generated = document_analysis.extract(snapshot, metadata, content, mode=mode)
            return self.store.apply("document/record", {"actor": actor, "case_id": metadata["case_id"], "analysis": generated}, authorize=authorize)
        finally:
            self.document_lock.release()


class Handler(BaseHTTPRequestHandler):
    timeout = 10

    def log_error(self, format, *args):
        # Parser errors can contain the raw request line, including credentials.
        self.log_message('HTTP request rejected')

    def log_request(self, code='-', size='-'):
        path = urlsplit(getattr(self, 'path', '')).path
        safe_path = path if re.fullmatch(r'/[A-Za-z0-9/_-]{0,159}', path) else '/redacted'
        command = getattr(self, 'command', None)
        method = command if command in ('GET', 'POST', 'HEAD', 'OPTIONS', 'PUT', 'DELETE', 'PATCH') else 'OTHER'
        self.log_message('%s %s %s', method, safe_path, str(code))

    def record_access(self, status):
        path = urlsplit(self.path).path
        if not path.startswith('/api/') or getattr(self, '_access_recorded', False):
            return True
        self._access_recorded = True
        safe_path = path if re.fullmatch(r'/[A-Za-z0-9/_-]{0,159}', path) else '/api/invalid'
        selected = parse_qs(urlsplit(self.path).query).get('case_id', [''])[0]
        if selected and re.fullmatch(r'[A-Za-z0-9_-]{1,64}', selected) and len(safe_path) + len(selected) < 150:
            safe_path += '/case/' + selected
        user = getattr(self, '_audit_user', None)
        mode = 'local-auth' if user else 'anonymous' if self.server.access else 'local-demo'
        actor = user['id'] if user else 'anonymous' if self.server.access else 'local-demo'
        event = ('login' if path == '/api/login' else 'logout' if path == '/api/logout' else
                 'denial' if status in (401, 403) else 'export' if path.endswith('/export') else
                 'download' if re.fullmatch(r'/api/evidence/EVD-[0-9]{4}', path) else
                 'read' if self.command == 'GET' else 'write')
        try:
            self.server.access_audit.append(actor=actor, mode=mode, event=event, target=safe_path,
                outcome='success' if status < 400 else 'denied' if status in (401, 403, 429) else 'error',
                ip=self.client_address[0])
            return True
        except (sqlite3.Error, ValueError, TypeError, KeyError, OverflowError):
            return False

    def send(self, status, content_type, payload, cookie=None, download=None):
        if not self.record_access(status):
            status, content_type = 503, 'application/json; charset=utf-8'
            payload = json.dumps({'error': 'Trilha de acesso indisponível. A resposta foi bloqueada; confira o estado antes de repetir uma alteração.'}).encode()
            cookie = download = None
        self.send_response(status)
        if cookie is not None:
            self.send_header("Set-Cookie", cookie)
        if download is not None:
            self.send_header("Content-Disposition", f'attachment; filename="{download}"')
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        # Only authorize inline scripts from the compiled, locally served HTML.
        hashes = []
        if content_type.startswith("text/html"):
            for attributes, script in re.findall(r"<script\b([^>]*)>(.*?)</script\s*>", payload.decode("utf-8"), re.I | re.S):
                if not re.search(r"\bsrc\s*=", attributes, re.I):
                    digest = base64.b64encode(hashlib.sha256(script.encode("utf-8")).digest()).decode("ascii")
                    hashes.append(f"'sha256-{digest}'")
        script_policy = " ".join(["'self'", "https://cdn.ui.porsche.com", *hashes])
        self.send_header("Content-Security-Policy", f"default-src 'self'; script-src {script_policy}; style-src 'self' 'unsafe-inline'; font-src 'self' https://cdn.ui.porsche.com; connect-src 'self' https://cdn.ui.porsche.com; img-src 'self' data: https://cdn.ui.porsche.com; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(payload)

    def send_json(self, status, data, cookie=None):
        self.send(status, "application/json; charset=utf-8", json.dumps(data, ensure_ascii=False).encode("utf-8"), cookie=cookie)

    def session_token(self):
        try:
            parsed = SimpleCookie(self.headers.get("Cookie", ""))
            return parsed[SESSION_COOKIE].value if SESSION_COOKIE in parsed else None
        except CookieError:
            return None

    def current_user(self, required=True):
        if not self.server.access:
            return None
        user = self.server.access.session(self.session_token())
        if user:
            self._audit_user = user
        if required and not user:
            raise WorkflowError("Entre para continuar. Sua sessão pode ter expirado.", 401)
        return user

    def session_state(self, user):
        return {"auth_required": self.server.access is not None, "authenticated": user is not None, "user": user,
                "mode": "local-auth" if self.server.access else "local-demo"}

    def session_cookie(self, token=None):
        age = int(self.server.access.session_ttl) if token and self.server.access else 0
        return f"{SESSION_COOKIE}={token or ''}; Path=/; Max-Age={age}; HttpOnly; SameSite=Strict"

    def authorizer(self, command, data):
        if not self.server.access:
            return None
        # Called inside the Store write transaction against the exact snapshot being changed.
        def authorize(snapshot):
            user = self.current_user()
            self.server.access.authorize(user, command, snapshot, data)
            return {"mode": "local-auth", "user_id": user["id"]}
        return authorize

    def valid_host(self):
        port = self.server.server_port
        return self.headers.get("Host") in {f"127.0.0.1:{port}", f"localhost:{port}"}

    def valid_origin(self):
        origin = self.headers.get("Origin")
        allowed = {"http://" + self.headers.get("Host", "")}
        if self.server.frontend_port:
            allowed.update(f"http://{host}:{self.server.frontend_port}" for host in ("127.0.0.1", "localhost"))
        return origin is None or origin in allowed

    def do_GET(self):
        self._audit_user, self._access_recorded = None, False
        if not self.valid_host():
            self.send_json(403, {"error": "Use o endereço local do Elo."})
            return
        path = urlsplit(self.path).path
        if path == "/api/session":
            self.send_json(200, self.session_state(self.current_user(required=False)))
            return
        if path.startswith("/api/"):
            try:
                user = self.current_user()
                if self.server.access:
                    self.server.access.authorize(user, "read")
            except WorkflowError as error:
                self.send_json(error.status, {"error": str(error)})
                return
        if re.fullmatch(r"/api/evidence/EVD-[0-9]{4}", path):
            try:
                from evidence import download_filename
                metadata, content = self.server.store.evidence_file(path.rsplit("/", 1)[-1])
                self.send(200, metadata["media_type"], content, download=download_filename(metadata))
            except WorkflowError as error:
                self.send_json(error.status, {"error": str(error)})
            except sqlite3.Error:
                self.send_json(503, {"error": "Banco indisponível. Tente novamente."})
        elif path == "/api/work/summary":
            try:
                self.send_json(200, work.summary(self.server.store.read()))
            except WorkflowError as error:
                self.send_json(error.status, {"error": str(error)})
            except sqlite3.Error:
                self.send_json(503, {"error": "Banco indisponível. Tente novamente."})
        elif path == "/api/insights":
            try:
                import insights
                snapshot = self.server.store.read(parse_qs(urlsplit(self.path).query).get("case_id", [None])[0])
                require(snapshot["audit_valid"], "A integridade da trilha precisa ser verificada.")
                case_id = snapshot["case"]["id"] if snapshot["case"] else None
                self.send_json(200, {"connections": insights.connections(snapshot, case_id) if case_id else None,
                    "memory": insights.similar_cases(snapshot, case_id) if case_id else None,
                    "trends": insights.trends(snapshot), "correlation": insights.correlated_cases(snapshot, case_id), "scenarios": snapshot.get("scenarios", [])})
            except WorkflowError as error:
                self.send_json(error.status, {"error": str(error)})
            except sqlite3.Error:
                self.send_json(503, {"error": "Banco indisponível. Tente novamente."})
        elif path == "/api/people":
            self.send_json(200, {"people": self.server.access.people() if self.server.access else []})
        elif path == "/api/supervision":
            try:
                import supervision
                snapshot = self.server.store.read()
                require(snapshot["audit_valid"], "A integridade da trilha precisa ser verificada.")
                summary = supervision.summary(snapshot)
                if self.server.access:
                    summary["identity_scope"] = "Modo atual: identidades locais autenticadas; o histórico pode incluir registros autodeclarados ou de serviço. Consulte a origem de cada evento. Provedor corporativo não configurado."
                self.send_json(200, summary)
            except WorkflowError as error:
                self.send_json(error.status, {"error": str(error)})
            except sqlite3.Error:
                self.send_json(503, {"error": "Banco indisponível. Tente novamente."})
        elif path == "/api/laboratory":
            try:
                import laboratory
                import rule_config
                rule_id = parse_qs(urlsplit(self.path).query).get("rule_id", ["contact-code-match"])[0]
                snapshot = self.server.store.read()
                require(snapshot["audit_valid"], "A integridade da trilha precisa ser verificada.")
                config = rule_config.get_config(snapshot, rule_id)
                self.send_json(200, laboratory.run_laboratory(rule_id=rule_id, config=config))
            except WorkflowError as error:
                self.send_json(error.status, {"error": str(error)})
            except sqlite3.Error:
                self.send_json(503, {"error": "Banco indisponível. Tente novamente."})
        elif path == "/api/access-audit/export":
            try:
                if self.server.access:
                    self.server.access.authorize(user, 'access-audit/export')
                if not self.record_access(200):
                    self.send_json(503, {"error": "Trilha de acesso indisponível."})
                    return
                self.send_json(200, self.server.access_audit.export())
            except WorkflowError as error:
                self.send_json(error.status, {"error": str(error)})
            except (ValueError, sqlite3.Error, TypeError, KeyError, OverflowError):
                self.send_json(503, {"error": "Trilha de acesso indisponível."})
        elif path == "/api/audit/export":
            try:
                self.send_json(200, build_export(self.server.store.export_state(include_files=True)))
            except WorkflowError as error:
                self.send_json(error.status, {"error": str(error)})
            except sqlite3.Error:
                self.send_json(503, {"error": "Banco indisponível. Tente novamente."})
        elif path == "/api/state":
            try:
                self.send_json(200, {**self.server.store.read(parse_qs(urlsplit(self.path).query).get("case_id", [None])[0]), "ai_configured": dossier.configured()})
            except WorkflowError as error:
                self.send_json(error.status, {"error": str(error)})
            except sqlite3.Error:
                self.send_json(503, {"error": "Banco indisponível. Tente novamente."})
        elif path == "/health":
            self.send_json(200, {"status": "ok"})
        elif self.server.static_dir and not path.startswith("/api/"):
            relative = "index.html" if path == "/" else unquote(path).lstrip("/")
            target = (self.server.static_dir / relative).resolve()
            if not target.is_relative_to(self.server.static_dir) or not target.is_file():
                self.send_json(404, {"error": "Página não encontrada."})
                return
            content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            self.send(200, content_type, target.read_bytes())
        else:
            self.send_json(404, {"error": "Página não encontrada."})

    def do_POST(self):
        self._audit_user, self._access_recorded = None, False
        if not self.valid_host() or not self.valid_origin():
            self.send_json(403, {"error": "Origem inválida."})
            return
        path = urlsplit(self.path).path
        command = path.removeprefix("/api/")
        if not path.startswith("/api/") or command not in COMMANDS | {"login", "logout"}:
            self.send_json(404, {"error": "Ação não encontrada."})
            return
        try:
            # Preflight rejects an already corrupt/unavailable ledger before side effects.
            # Business changes keep their own transactional audit; the HTTP receipt is separate.
            try:
                self.server.access_audit.export()
            except (ValueError, sqlite3.Error, TypeError, KeyError, OverflowError) as error:
                raise WorkflowError("Verifique a integridade da trilha de acesso antes de continuar.", 503) from error
            user = self.current_user() if command != "login" else None
            if self.headers.get_content_type() != "application/json":
                raise WorkflowError("Use application/json.", 415)
            length = int(self.headers.get("Content-Length", "0"))
            if length > (1500000 if command == "evidence/upload" else 524288 if command in {"import", "import/preview", "import/file"} else 65536 if command in governance.COMMANDS | work.COMMANDS | {"rule/config"} else 8192):
                raise WorkflowError("O pedido é grande demais.", 413)
            if length <= 0:
                raise ValueError
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError
            if command == "login":
                require(self.server.access is not None, "Autenticação local não configurada.")
                token, user = self.server.access.login(data.get("username"), data.get("password"))
                self._audit_user = user
                self.server.access.logout(self.session_token())
                self.send_json(200, self.session_state(user), cookie=self.session_cookie(token))
                return
            if command == "logout":
                if self.server.access:
                    self.server.access.logout(self.session_token())
                self.send_json(200, self.session_state(None), cookie=self.session_cookie())
                return
            if user:
                data["actor"] = user["id"]
            authorize = self.authorizer("import" if command in {"import/preview", "import/file"} else command, data)
            if command in {"import/preview", "import/file"}:
                import tabular_import
                snapshot = self.server.store.read()
                if authorize:
                    authorize(snapshot)
                require(data.get("synthetic") is True, "Confirme que todos os dados são fictícios.")
                try:
                    preview = tabular_import.preview(data, snapshot["dataset"])
                except tabular_import.ImportFormatError as error:
                    raise WorkflowError(str(error), 422) from error
                if command == "import/preview":
                    self.send_json(200, preview)
                    return
                require(preview["ready"], "Corrija os erros e valide o mapeamento antes de importar.")
                state = self.server.store.apply("import", {"actor": required(data, "actor", 80),
                    "synthetic": True, "dataset": preview["dataset"]}, authorize=authorize)
            elif command == "evidence/analyze":
                state = self.server.analyze_document(data, authorize=authorize)
            elif command == "assistant/query":
                state = self.server.consult(data, authorize=authorize)
            elif command == "dossier":
                state = self.server.summarize(choice(data, "mode", ("local", "real")), data.get("case_id"),
                                              actor=user["id"] if user else None, authorize=authorize)
            else:
                state = self.server.store.apply(command, data, authorize=authorize)
            self.send_json(200, {**state, "ai_configured": dossier.configured()})
        except ValueError:
            self.send_json(400, {"error": "Pedido JSON inválido."})
        except WorkflowError as error:
            self.send_json(error.status, {"error": str(error)})
        except sqlite3.Error:
            self.send_json(503, {"error": "Banco indisponível. Tente novamente."})


def serve():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--db", type=Path, default=Path(os.getenv("ELO_DB", ROOT / "data/elo.sqlite3")))
    parser.add_argument("--dist", type=Path, help="Serve the compiled Vite build from this directory.")
    parser.add_argument("--frontend-port", type=int, help="Trusted loopback Vite port for development only.")
    args = parser.parse_args()
    if args.frontend_port is not None and not 1 <= args.frontend_port <= 65535:
        parser.error("--frontend-port must be a valid TCP port")
    args.db.parent.mkdir(parents=True, exist_ok=True)
    with EloServer(("127.0.0.1", args.port), Store(args.db), args.dist, args.frontend_port) as server:
        print(f"Elo API: http://127.0.0.1:{server.server_port}", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    serve()
