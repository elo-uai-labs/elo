import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from supervision import summary
from domain import WorkflowError


class SupervisionTest(unittest.TestCase):
    def test_denominators_separate_models_and_empty_sample(self):
        empty = summary({"audit_valid": True, "cases": [], "audit": []})
        self.assertIsNone(empty["groups"][0]["agreement_rate"])
        cases = [{"id": str(i), "dossier": {"mode": mode},
                  "decision": {"review": review, "reason": "Contexto sintético"}}
                 for i, (mode, review) in enumerate((("real", "accept"), ("real", "reject"), ("local", "accept")))]
        result = summary({"audit_valid": True, "cases": cases + [{"id": "pending"}], "audit": []})
        self.assertEqual(result["groups"][0]["agreement_rate"], .5)
        self.assertEqual(result["groups"][1]["agreement_rate"], 1)
        self.assertEqual(len(result["groups"][0]["disagreements"]), 1)
        self.assertEqual(result["pending"], 1)

    def test_heuristic_requires_five_fast_accepts_for_same_reviewer(self):
        events = []
        for index in range(5):
            details = {"case_id": str(index), "revision": str(index)}
            events.append({"action": "Dossiê registrado", "details": details, "at": "2026-11-22T10:00:00+00:00"})
            events.append({"action": "Decisão humana registrada", "actor": "Analista fictício", "seq": len(events)+1,
                           "details": {"case_id": str(index), "dossier_revision": str(index), "review": "accept"},
                           "at": "2026-11-22T10:00:02+00:00"})
        state = {"audit_valid": True, "cases": [], "audit": events}
        self.assertEqual(len(summary(state)["alerts"]), 1)
        self.assertEqual(summary(state)["identity_counts"], {"authenticated_decisions": 0, "legacy_or_declared_decisions": 5})
        events[-1]["authentication"] = {"mode": "local-auth", "user_id": "analista"}
        self.assertEqual(summary(state)["identity_counts"], {"authenticated_decisions": 1, "legacy_or_declared_decisions": 4})
        self.assertEqual(summary(state)["alerts"], [], "Identidades autenticadas não herdam aceitações autodeclaradas homônimas")
        events[-1]["details"]["review"] = "adjust"
        self.assertEqual(summary(state)["alerts"], [])
        events[-1]["details"]["review"] = "accept"
        events[-1]["at"] = "2026-11-22T10:01:00+00:00"
        self.assertEqual(summary(state)["alerts"], [])

    def test_records_preserve_current_revision_and_identity_without_backfilling(self):
        decision = {"actor": "Ana Demo", "review": "adjust", "reason": "Conferir original", "dossier_revision": "current"}
        event = {"action": "Decisão humana registrada", "actor": "Ana Demo", "seq": 2,
                 "at": "2026-11-23T13:00:00+00:00", "details": {"case_id": "C1", **decision},
                 "authentication": {"mode": "local-auth"}}
        snapshot = {"audit_valid": True, "audit": [event], "cases": [
            {"id": "C1", "dossier": {"mode": "real"}, "decision": decision},
            {"id": "C2", "dossier": {"mode": "local"}, "decision": decision}]}
        records = summary(snapshot)["records"]
        self.assertEqual(records[0]["identity_mode"], "local-auth")
        self.assertEqual(records[0]["at"], event["at"])
        self.assertEqual(records[1]["identity_mode"], "local-demo")
        self.assertIsNone(records[1]["at"])
        event["details"]["dossier_revision"] = "old"
        self.assertIsNone(summary(snapshot)["records"][0]["at"])

    def test_invalid_audit_is_rejected(self):
        with self.assertRaises(WorkflowError):
            summary({"audit_valid": False})
