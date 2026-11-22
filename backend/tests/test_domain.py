import os
import sqlite3
import tempfile
import unittest
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dossier
from domain import Store, WorkflowError


class WorkflowTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "demo.sqlite3"
        self.store = Store(self.path)

    def analyze(self):
        state = self.store.apply("detect", {})
        local = dossier.generate(state["case"]["evidence"], "local")
        return self.store.apply("dossier", local)

    def decide(self, outcome="qualify"):
        revision = self.store.read()["case"]["dossier"]["revision"]
        return self.store.apply("decision", {"actor": "Analista demo", "reason": "Investigar o vínculo", "outcome": outcome, "review": "adjust", "dossier_revision": revision})

    def test_linked_workflow_and_persistence(self):
        state = self.analyze()
        self.assertEqual(state["case"]["dossier"]["source_ids"], ["CTR-1042", "FOR-031", "EMP-014"])
        state = self.decide()
        self.assertEqual(state["risk"]["level"], "Moderada")
        self.assertEqual([impact["status"] for impact in state["case"]["impacts"]], ["pending", "pending"])
        self.store.apply("impact", {"kind": "risk", "outcome": "approved", "actor": "Risco demo", "reason": "Revisar exposição"})
        self.store.apply("impact", {"kind": "maturity", "outcome": "rejected", "actor": "Maturidade demo", "reason": "Manter avaliação até obter dados"})
        state = self.store.apply("action", {"actor": "Analista demo", "title": "Revisar cadastro", "owner": "Gestor demo", "due": "2027-01-15"})
        action = state["actions"][0]
        self.assertEqual(action["case_id"], state["case"]["id"])
        with self.assertRaises(WorkflowError):
            self.store.apply("action/update", {"id": action["id"], "status": "done", "actor": "Gestor demo"})
        self.store.apply("action/update", {"id": action["id"], "status": "done", "actor": "Gestor demo", "evidence": "Ata sintética", "action_revision": action["revision"]})
        pending = self.store.read()["actions"][0]
        self.assertEqual(pending["status"], "closure_requested")
        self.store.apply("action/close", {"id": action["id"], "action_revision": pending["revision"], "actor": "Revisor independente", "reason": "Evidência conferida", "outcome": "approved"})
        state = Store(self.path).read()
        self.assertEqual(state["risk"]["level"], "Alta")
        self.assertEqual(state["maturity"]["level"], "Intermediária")
        self.assertEqual(state["actions"][0]["status"], "done")
        self.assertTrue(state["audit_valid"])
        self.assertEqual(len(state["audit"]), 8)

    def test_nonqualified_case_cannot_change_other_modules(self):
        revision = self.analyze()["case"]["dossier"]["revision"]
        with self.assertRaises(WorkflowError):
            self.store.apply("decision", {"actor": "Analista demo", "outcome": "qualify", "review": "accept", "reason": " ", "dossier_revision": revision})
        state = self.decide("monitor")
        self.assertEqual(state["case"]["impacts"], [])
        with self.assertRaises(WorkflowError):
            self.store.apply("impact", {"actor": "Analista demo", "kind": "risk", "outcome": "approved", "reason": "teste"})
        self.assertEqual(len(self.store.read()["audit"]), 3)

    def test_decision_cannot_accept_a_newer_unseen_dossier(self):
        case = self.analyze()["case"]
        replacement = dossier.generate(case["evidence"], "local")
        replacement["text"] += " Revisão da síntese."
        self.store.apply("dossier", replacement)
        with self.assertRaises(WorkflowError) as error:
            self.store.apply("decision", {"actor": "Analista demo", "outcome": "qualify", "review": "accept", "reason": "Com base na versão anterior", "dossier_revision": case["dossier"]["revision"]})
        self.assertEqual(error.exception.status, 409)
        self.assertIsNone(self.store.read()["case"]["decision"])
        self.assertEqual(len(self.store.read()["audit"]), 3)

    def test_concurrent_detection_creates_one_case_and_event(self):
        def detect(_):
            try:
                self.store.apply("detect", {})
            except WorkflowError as error:
                return error.status
            return 200

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(detect, range(8)))
        self.assertEqual(results.count(200), 1)
        self.assertEqual(results.count(409), 7)
        self.assertEqual(len(self.store.read()["audit"]), 1)

    def test_audit_is_append_only_and_detects_privileged_tampering(self):
        self.analyze()
        with sqlite3.connect(self.path) as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE audit SET hash = 'corrupted' WHERE seq = 1")
            db.execute("DROP TRIGGER audit_no_update")
            db.execute("UPDATE audit SET hash = 'corrupted' WHERE seq = 1")
        self.assertFalse(self.store.read()["audit_valid"])
        with self.assertRaises(WorkflowError):
            self.decide()

    def test_real_ai_unconfigured_does_not_claim_local_output(self):
        state = self.store.apply("detect", {})
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(WorkflowError) as error:
                dossier.generate(state["case"]["evidence"], "real")
        self.assertEqual(error.exception.status, 503)
        self.assertIsNone(self.store.read()["case"]["dossier"])
