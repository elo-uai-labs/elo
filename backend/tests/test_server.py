import json
import base64
import sys
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from domain import Store
from server import EloServer


class ServerTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.dist = self.root / "dist"
        self.dist.mkdir()
        (self.dist / "index.html").write_text('<!doctype html><script>window.loader = true;</script><p-text>Elo</p-text>')
        (self.root / "secret.txt").write_text("do-not-serve")
        self.store = Store(self.root / "state.sqlite3")
        self.server = EloServer(("127.0.0.1", 0), self.store, self.dist, 5173, access_service=None)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.shutdown)

    def shutdown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def request(self, method="GET", path="/api/state", data=None, headers=None):
        connection = HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        self.addCleanup(connection.close)
        body = json.dumps(data) if data is not None else None
        all_headers = {"Content-Type": "application/json", **(headers or {})}
        connection.request(method, path, body, all_headers)
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), response.read()

    def test_real_api_and_trusted_dev_origin(self):
        status, _, body = self.request("POST", "/api/detect", {}, {"Origin": "http://127.0.0.1:5173"})
        self.assertEqual(status, 200)
        state = json.loads(body)
        self.assertEqual(state["case"]["id"], "ELO-1042")
        self.assertTrue(state["audit_valid"])
        status, _, body = self.request()
        self.assertEqual(json.loads(body)["case"], state["case"])

    def test_import_case_selection_and_export_http(self):
        batch = {"actor": "Importador", "synthetic": True, "dataset": {
            "employees": [], "suppliers": [],
            "contracts": [{"id": "CTR-NEW", "title": "Novo contrato fictício", "approver_id": "EMP-014", "supplier_id": "FOR-031"}]}}
        self.assertEqual(self.request("POST", "/api/import", batch)[0], 200)
        status, _, body = self.request("POST", "/api/detect", {})
        self.assertEqual(status, 200)
        self.assertEqual(len(json.loads(body)["cases"]), 2)
        status, _, body = self.request(path="/api/state?case_id=ELO-NEW")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["case"]["id"], "ELO-NEW")
        status, _, body = self.request("POST", "/api/dossier", {"case_id": "ELO-NEW", "mode": "local"})
        self.assertEqual(status, 200)
        self.assertIn("CTR-NEW", json.loads(body)["case"]["dossier"]["source_ids"])
        self.assertIsNone(self.store.read()["case"]["dossier"])
        self.assertEqual(self.request(path="/api/state?case_id=missing")[0], 409)
        self.assertEqual(self.request(path="/api/audit/export")[0], 200)

    def test_evidence_http_forces_download_and_export_has_bytes(self):
        self.request("POST", "/api/detect", {})
        payload = {"case_id": "ELO-1042", "actor": "Analista", "name": "ata.txt", "media_type": "text/plain",
                   "description": "Evidência sintética", "synthetic": True, "content_base64": base64.b64encode(b"Ata sintetica").decode()}
        status, _, body = self.request("POST", "/api/evidence/upload", payload)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["attachments"][0]["id"], "EVD-0001")
        status, headers, body = self.request(path="/api/evidence/EVD-0001")
        self.assertEqual(status, 200)
        self.assertEqual(body, b"Ata sintetica")
        self.assertEqual(headers["Content-Disposition"], 'attachment; filename="EVD-0001.txt"')
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        status, _, body = self.request(path="/api/audit/export")
        self.assertEqual(status, 200)
        package = json.loads(body)
        self.assertEqual(package["files"][0]["content_base64"], payload["content_base64"])
        self.assertEqual(self.request(path="/api/evidence/EVD-9999")[0], 404)

    def test_rejects_untrusted_origin_and_host_without_writes(self):
        for origin in ("https://attacker.example", "null", "http://127.0.0.1:51730"):
            self.assertEqual(self.request("POST", "/api/detect", {}, {"Origin": origin})[0], 403)
        self.assertEqual(self.request(headers={"Host": "attacker.example"})[0], 403)
        self.assertIsNone(self.store.read()["case"])
        self.assertEqual(self.store.read()["audit"], [])

    def test_serves_build_with_hashed_loader_and_font_permission(self):
        status, headers, body = self.request(path="/")
        self.assertEqual(status, 200)
        self.assertIn(b"<p-text>Elo</p-text>", body)
        policy = headers["Content-Security-Policy"]
        self.assertIn("'sha256-", policy)
        self.assertIn("font-src 'self' https://cdn.ui.porsche.com", policy)
        self.assertNotIn("'unsafe-inline'", policy.split("script-src ")[1].split(";")[0])

    def test_build_server_cannot_read_files_outside_dist(self):
        (self.dist / "linked.txt").symlink_to(self.root / "secret.txt")
        for path in ("/../secret.txt", "/%2e%2e/secret.txt", "/linked.txt", "/api/missing", "/backend/fixture.json"):
            status, _, body = self.request(path=path)
            self.assertEqual(status, 404, path)
            self.assertNotIn(b"do-not-serve", body)

    def test_rejects_invalid_input_without_mutating(self):
        status, _, _ = self.request("POST", "/api/detect", [], {})
        self.assertEqual(status, 400)
        self.assertEqual(self.request("POST", "/api/detect", {}, {"Content-Type": "text/plain"})[0], 415)
        self.assertEqual(self.request("POST", "/api/detect", {"padding": "x" * 8192})[0], 413)
        self.assertEqual(self.store.read()["audit"], [])


if __name__ == "__main__":
    unittest.main()
