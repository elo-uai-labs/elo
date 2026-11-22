"""Local Elo API and the compiled Porsche Design System application."""

import argparse
import base64
import hashlib
import json
import mimetypes
import os
import re
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from urllib.parse import parse_qs, unquote, urlsplit

import dossier
import governance
from audit_export import build_export
from domain import Store, WorkflowError, choice, require

ROOT = Path(__file__).resolve().parent.parent
COMMANDS = {"import", "detect", "dossier", "decision", "impact", "action", "action/update", "action/edit", "action/close", *governance.COMMANDS}


class EloServer(ThreadingHTTPServer):
    request_queue_size = 64
    daemon_threads = True

    def __init__(self, address, store, static_dir=None, frontend_port=None):
        self.store = store
        self.static_dir = Path(static_dir).resolve() if static_dir else None
        self.frontend_port = frontend_port
        self.dossier_lock = Lock()
        super().__init__(address, Handler)

    def summarize(self, mode, case_id=None):
        require(self.dossier_lock.acquire(blocking=False), "Já existe uma síntese em andamento.")
        try:
            snapshot = self.store.read(case_id)
            require(snapshot["audit_valid"], "A integridade da trilha precisa ser verificada.")
            case = snapshot["case"]
            require(case and not case["decision"], "O caso precisa estar aguardando análise.")
            return self.store.apply("dossier", {**dossier.generate(case["evidence"], mode), "case_id": case["id"]})
        finally:
            self.dossier_lock.release()


class Handler(BaseHTTPRequestHandler):
    timeout = 10

    def send(self, status, content_type, payload):
        self.send_response(status)
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

    def send_json(self, status, data):
        self.send(status, "application/json; charset=utf-8", json.dumps(data, ensure_ascii=False).encode("utf-8"))

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
        if path == "/api/supervision":
            try:
                import supervision
                snapshot = self.server.store.read()
                require(snapshot["audit_valid"], "A integridade da trilha precisa ser verificada.")
                self.send_json(200, supervision.summary(snapshot))
            except WorkflowError as error:
                self.send_json(error.status, {"error": str(error)})
            except sqlite3.Error:
                self.send_json(503, {"error": "Banco indisponível. Tente novamente."})
        elif path == "/api/laboratory":
            import laboratory
            self.send_json(200, laboratory.run_laboratory())
        elif path == "/api/audit/export":
            try:
                self.send_json(200, build_export(self.server.store.export_state()))
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
        if not path.startswith("/api/") or command not in COMMANDS:
            self.send_json(404, {"error": "Ação não encontrada."})
            return
        try:
            if self.headers.get_content_type() != "application/json":
                raise WorkflowError("Use application/json.", 415)
            length = int(self.headers.get("Content-Length", "0"))
            if length > (524288 if command == "import" else 65536 if command in governance.COMMANDS else 8192):
                raise WorkflowError("O pedido é grande demais.", 413)
            if length <= 0:
                raise ValueError
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError
            if command == "dossier":
                state = self.server.summarize(choice(data, "mode", ("local", "real")), data.get("case_id"))
            else:
                state = self.server.store.apply(command, data)
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
