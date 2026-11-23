import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from domain import Store, WorkflowError
from insights import connections, similar_cases, simulate, trends


class InsightsTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.store = Store(Path(directory.name) / "insights.sqlite3")
        self.state = self.store.apply("detect", {})

    def test_connections_reference_existing_nodes(self):
        result = connections(self.state)
        ids = {node["id"] for node in result["nodes"]}
        self.assertIn("RSK-001", ids)
        self.assertIn("EMP-014", ids)
        self.assertTrue(all(edge["source"] in ids and edge["target"] in ids for edge in result["edges"]))

    def test_memory_requires_reviewed_other_case_and_explains_score(self):
        self.assertEqual(similar_cases(self.state)["matches"], [])
        other = deepcopy(self.state["case"])
        other.update(id="ELO-OTHER", decision={"outcome": "discard", "reason": "Contexto revisado"})
        self.state["cases"].append(other)
        match = similar_cases(self.state)["matches"][0]
        self.assertEqual(match["score"], 6)
        self.assertEqual(len(match["reasons"]), 4)

    def test_scenario_preserves_real_risk_and_refuses_stale_input(self):
        before = deepcopy(self.state["risks"])
        payload = {"actor": "Analista", "reason": "Hipótese sintética", "risk_id": "RSK-001",
                   "risk_revision": self.state["risk"]["revision"], "likelihood": 5, "impact": 5}
        event = simulate(self.state, payload)
        self.assertEqual(event[2]["hypothetical_level"], "Crítica")
        self.assertEqual(self.state["risks"], before)
        with self.assertRaises(WorkflowError):
            simulate(self.state, {**payload, "risk_revision": "stale"})

    def test_trends_count_audit_events_in_declared_timezone(self):
        result = trends(self.state)
        self.assertEqual(sum(row["detected"] for row in result["periods"]), 1)
        self.assertEqual(result["timezone"], "America/Sao_Paulo")
        legacy = {"action": "Recomendação atualizada", "at": "2026-11-01T01:00:00+00:00", "details": {"id": "REC-OLD", "status": "done"}}
        self.state["audit"].extend([legacy, deepcopy(legacy)])
        periods = {row["period"]: row for row in trends(self.state)["periods"]}
        self.assertEqual(periods["2026-10"]["completed"], 1)
        self.state["audit"].append({"action": "Integração sintética executada", "at": "2026-11-02T10:00:00+00:00", "details": {"case_ids": ["SIG-SUP-CTR-NEW", "ELO-NEW"]}})
        self.assertEqual(sum(row["detected"] for row in trends(self.state)["periods"]), 3)
