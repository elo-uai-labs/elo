import copy
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audit_export import build_export, verify_export
from domain import Store, WorkflowError


class ExportTest(unittest.TestCase):
    def test_round_trip_and_independent_tamper_detection(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / "export.sqlite3")
            self.assertTrue(verify_export(build_export(store.export_state())))
            store.apply("detect", {})
            package = build_export(store.export_state())
            self.assertTrue(verify_export(package))
            for mutate in (
                lambda p: p["state"]["risk"].update(level="Baixa"),
                lambda p: p["events"][0].update(actor="Outro"),
                lambda p: p["events"].clear(),
                lambda p: p["manifest"].update(event_count=99),
            ):
                changed = copy.deepcopy(package)
                mutate(changed)
                self.assertFalse(verify_export(changed))

    def test_invalid_snapshots_are_not_exported(self):
        with self.assertRaises(WorkflowError):
            build_export({"audit_valid": False})
        for malformed in (None, [], {}, {"format": "unknown"}):
            self.assertFalse(verify_export(malformed))
