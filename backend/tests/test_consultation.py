import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from domain import Store, WorkflowError
from consultation import prepare, answer, record


class ConsultationTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        store = Store(Path(directory.name) / "consultation.sqlite3")
        self.state = store.apply("detect", {})
        self.query = {"question": "Qual é a exposição do risco?", "case_id": "ELO-1042", "mode": "local"}

    def test_local_sources_and_history_do_not_change_business_state(self):
        before = deepcopy(self.state)
        result = answer(prepare(self.state, self.query))
        self.assertEqual(result["mode"], "local")
        self.assertTrue(any("RSK-001" in claim["source_ids"] for claim in result["claims"]))
        record(self.state, {"actor": "Analista", "answer": result})
        self.assertEqual(self.state["risk"], before["risk"])
        self.assertEqual(self.state["case"], before["case"])
        self.assertEqual(len(self.state["assistant_queries"]), 1)

    def test_abstention_and_unknown_source_rejection(self):
        context = prepare(self.state, {**self.query, "mode": "real"})
        result = answer(context, generator=lambda *_: {"mode": "real", "model": "test", "claims": [], "limitations": "Fontes insuficientes", "suggestion": "Consulte as fontes"})
        self.assertTrue(result["abstained"])
        with self.assertRaises(WorkflowError):
            answer(context, generator=lambda *_: {"mode": "real", "model": "test", "claims": [{"text": "Afirmação", "source_ids": ["CTR-OUTRO"]}], "limitations": "Revisão necessária", "suggestion": "Verifique"})

    def test_context_never_includes_unrelated_case_or_file_bytes(self):
        other = deepcopy(self.state["case"])
        other.update(id="ELO-OTHER")
        other["evidence"][0]["detail"] = "SEGREDO DE OUTRO CASO"
        self.state["cases"].append(other)
        self.state["attachments"] = [{"case_id": "ELO-1042", "name": "arquivo.txt", "content_base64": "NOT-SENT"}]
        context = prepare(self.state, self.query)
        self.assertNotIn("SEGREDO", str(context))
        self.assertNotIn("NOT-SENT", str(context))

    def test_rejects_unknown_entities_wrong_mode_and_stale_sources(self):
        context = prepare(self.state, {**self.query, "mode": "real"})
        valid = {"mode": "real", "model": "test", "claims": [{"text": "O risco é moderado.", "source_ids": ["RSK-001"]}], "limitations": "Fontes do caso", "suggestion": "Revise"}
        for change in ({"mode": "local"}, {"model": None}, {"extra": "untrusted"}, {"claims": [{"text": "RSK-UNKNOWN é crítico.", "source_ids": ["RSK-001"]}]}):
            with self.assertRaises(WorkflowError):
                answer(context, generator=lambda *_: {**valid, **change})
        result = answer(context, generator=lambda *_: valid)
        self.state["risks"][0]["level"] = "Alta"
        with self.assertRaises(WorkflowError) as error:
            record(self.state, {"actor": "Analista", "answer": result})
        self.assertEqual(error.exception.status, 409)
        self.assertEqual(self.state.get("assistant_queries", []), [])

    def test_query_cap_checked_before_generation(self):
        self.state["assistant_queries"] = [{}] * 200
        with self.assertRaises(WorkflowError):
            prepare(self.state, self.query)
