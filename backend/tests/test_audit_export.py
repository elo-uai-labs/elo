import copy
import base64
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audit_export import build_export, digest, verify_export
from domain import Store, WorkflowError


class ExportTest(unittest.TestCase):
    def test_round_trip_and_independent_tamper_detection(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / "export.sqlite3")
            self.assertTrue(verify_export(build_export(store.export_state())))
            store.apply("detect", {})
            package = build_export(store.export_state())
            self.assertTrue(verify_export(package))
            legacy = copy.deepcopy(package)
            legacy["format"] = "elo-audit-v1"
            del legacy["files"]
            del legacy["manifest"]["files_hash"]
            self.assertTrue(verify_export(legacy))
            legacy["files"] = []
            self.assertFalse(verify_export(legacy), "Não aceitar payload extra sem verificação em v1")
            for mutate in (
                lambda p: p["state"]["risk"].update(level="Baixa"),
                lambda p: p["events"][0].update(actor="Outro"),
                lambda p: p["events"].clear(),
                lambda p: p["manifest"].update(event_count=99),
                lambda p: p.update(unverified="conteúdo extra"),
            ):
                changed = copy.deepcopy(package)
                mutate(changed)
                self.assertFalse(verify_export(changed))

    def test_invalid_snapshots_are_not_exported(self):
        with self.assertRaises(WorkflowError):
            build_export({"audit_valid": False})
        for malformed in (None, [], {}, {"format": "unknown"}):
            self.assertFalse(verify_export(malformed))

    def test_portable_files_detect_changed_missing_extra_and_legacy_downgrade(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / "files.sqlite3")
            store.apply("detect", {})
            store.apply("evidence/upload", {"actor": "Analista", "synthetic": True,
                "case_id": "ELO-1042", "name": "ata.txt", "media_type": "text/plain",
                "description": "Ata sintética", "content_base64": base64.b64encode(b"Ata sintetica.").decode()})
            package = build_export(store.export_state(include_files=True))
            self.assertTrue(verify_export(package))
            self.assertEqual(len(package["files"]), 1)
            for mutate in (
                lambda p: p["files"][0].update(content_base64=base64.b64encode(b"Adulterada").decode()),
                lambda p: p["files"].clear(),
                lambda p: p["files"].append(copy.deepcopy(p["files"][0])),
                lambda p: p["files"][0].update(id="EVD-INEXISTENTE"),
                lambda p: p["files"][0].update(content_base64="invalid!!"),
            ):
                changed = copy.deepcopy(package)
                mutate(changed)
                # Even recomputing the portable list checksum cannot bypass the
                # original metadata's size/hash and exact coverage requirements.
                changed["manifest"]["files_hash"] = digest(changed["files"])
                self.assertFalse(verify_export(changed))
            downgraded = copy.deepcopy(package)
            downgraded["format"] = "elo-audit-v1"
            del downgraded["files"]
            del downgraded["manifest"]["files_hash"]
            self.assertFalse(verify_export(downgraded))
