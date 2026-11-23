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
from access import AccessService
from audit_export import build_export
from domain import Store, WorkflowError, choice, require, required

ROOT = Path(__file__).resolve().parent.parent
SESSION_COOKIE = "elo_session"
COMMANDS = {"import", "detect", "dossier", "decision", "impact", "action", "action/update", "action/edit", "action/close", "evidence/upload", "scenario/create", "assistant/query", *governance.COMMANDS, *reporting.COMMANDS}


class EloServer(ThreadingHTTPServer):
    request_queue_size = 64
    daemon_threads = True

    def __init__(self, address, store, static_dir=None, frontend_port=None, access_service=...):
        self.access = AccessService.from_environment() if access_service is ... else access_service
        self.store = store
        self.static_dir = Path(static_dir).resolve() if static_dir else None
        self.frontend_port = frontend_port
        self.dossier_lock = Lock()
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


class Handler(BaseHTTPRequestHandler):
    timeout = 10

    def send(self, status, content_type, payload, cookie=None, download=None):
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
        elif path == "/api/insights":
            try:
                import insights
                snapshot = self.server.store.read(parse_qs(urlsplit(self.path).query).get("case_id", [None])[0])
                require(snapshot["audit_valid"], "A integridade da trilha precisa ser verificada.")
                case_id = snapshot["case"]["id"] if snapshot["case"] else None
                self.send_json(200, {"connections": insights.connections(snapshot, case_id) if case_id else None,
                    "memory": insights.similar_cases(snapshot, case_id) if case_id else None,
                    "trends": insights.trends(snapshot), "scenarios": snapshot.get("scenarios", [])})
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
            import laboratory
            self.send_json(200, laboratory.run_laboratory())
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
        if not self.valid_host() or not self.valid_origin():
            self.send_json(403, {"error": "Origem inválida."})
            return
        path = urlsplit(self.path).path
        command = path.removeprefix("/api/")
        if not path.startswith("/api/") or command not in COMMANDS | {"login", "logout"}:
            self.send_json(404, {"error": "Ação não encontrada."})
            return
        try:
            user = self.current_user() if command != "login" else None
            if self.headers.get_content_type() != "application/json":
                raise WorkflowError("Use application/json.", 415)
            length = int(self.headers.get("Content-Length", "0"))
            if length > (1500000 if command == "evidence/upload" else 524288 if command == "import" else 65536 if command in governance.COMMANDS else 8192):
                raise WorkflowError("O pedido é grande demais.", 413)
            if length <= 0:
                raise ValueError
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError
            if command == "login":
                require(self.server.access is not None, "Autenticação local não configurada.")
                token, user = self.server.access.login(data.get("username"), data.get("password"))
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
            authorize = self.authorizer(command, data)
            if command == "assistant/query":
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
