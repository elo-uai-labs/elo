import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dossier
from domain import DATASET, WorkflowError, match_case


class OnDeviceDossierTest(unittest.TestCase):
    def setUp(self):
        self.evidence = match_case(DATASET)["evidence"]
        self.ids = [item["id"] for item in self.evidence]
        self.invalid = {"claims": [{"text": "FOR-031 compartilha cadastro com EMP-014.", "source_ids": ["CTR-INEXISTENTE"]}],
                        "limitations": "A coincidência não comprova irregularidade.",
                        "suggestion": "Verifique o contexto.", "model": "test-model"}
        self.valid = {**self.invalid, "claims": [{"text": "CTR-1042 relaciona FOR-031 a EMP-014.", "source_ids": self.ids}]}

    def test_regenerates_instead_of_accepting_an_unknown_reference(self):
        results = [SimpleNamespace(stdout=json.dumps(item)) for item in (self.invalid, self.valid)]
        with patch("dossier.subprocess.run", side_effect=results) as run:
            result = dossier.generate_on_device("/test/model", self.evidence, self.ids)
        self.assertEqual(result["claims"], self.valid["claims"])
        self.assertEqual(result["source_ids"], self.ids)
        self.assertEqual(run.call_count, 2)
        repair = json.loads(run.call_args_list[1].kwargs["input"])
        self.assertIn("rejeitada", repair["instructions"])
        self.assertLessEqual(run.call_args_list[1].kwargs["timeout"], run.call_args_list[0].kwargs["timeout"])

    def test_invalid_regeneration_is_rejected_without_relaxing_validation(self):
        with patch("dossier.subprocess.run", return_value=SimpleNamespace(stdout=json.dumps(self.invalid))) as run:
            with self.assertRaises(WorkflowError) as error:
                dossier.generate_on_device("/test/model", self.evidence, self.ids)
        self.assertEqual(error.exception.status, 502)
        self.assertEqual(run.call_count, 2)

    def test_valid_first_generation_does_not_repeat_inference(self):
        with patch("dossier.subprocess.run", return_value=SimpleNamespace(stdout=json.dumps(self.valid))) as run:
            dossier.generate_on_device("/test/model", self.evidence, self.ids)
        self.assertEqual(run.call_count, 1)


class ClaimValidationTest(unittest.TestCase):
    def test_each_claim_must_have_its_own_existing_citations(self):
        from copy import deepcopy
        evidence = match_case(DATASET)["evidence"]
        result = dossier.generate(evidence, "local")
        self.assertEqual(len(result["claims"]), 2)
        self.assertEqual(result["prompt_version"], "elo-dossier-v3")
        for invalid_sources in ([], ["EMP-UNKNOWN"]):
            changed = deepcopy(result)
            changed["claims"][1]["source_ids"] = invalid_sources
            with self.assertRaises(ValueError):
                dossier.verified_dossier(changed, "model", result["source_ids"])
        changed = deepcopy(result)
        changed["claims"][0]["text"] += " EMP-INEXISTENTE."
        with self.assertRaises(ValueError):
            dossier.verified_dossier(changed, "model", result["source_ids"])

    def test_metadata_limits_and_required_caveats(self):
        evidence = match_case(DATASET)["evidence"]
        result = dossier.generate(evidence, "local")
        with self.assertRaises(ValueError):
            dossier.verified_dossier({**result, "limitations": ""}, "model", result["source_ids"])
        with self.assertRaises(ValueError):
            dossier.verified_dossier({**result, "suggestion": "x" * 2500}, "model", result["source_ids"])

    def test_structured_citations_do_not_require_repeated_ids_in_prose(self):
        result = dossier.verified_dossier({
            "claims": [{"text": "O contrato identifica fornecedor e aprovador.", "source_ids": ["CTR-1042"]}],
            "limitations": "O vínculo requer análise humana.", "suggestion": "Verifique o contexto."}, "model", ["CTR-1042"])
        self.assertEqual(result["claims"][0]["source_ids"], ["CTR-1042"])
        self.assertEqual(result["claims"][0]["text"], "O contrato identifica fornecedor e aprovador.")
