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
        self.invalid = {"text": "FOR-031 compartilha cadastro com EMP-014.", "source_ids": self.ids, "model": "test-model"}
        self.valid = {**self.invalid, "text": "CTR-1042 relaciona FOR-031 a EMP-014. A coincidência cadastral exige verificação humana."}

    def test_regenerates_instead_of_accepting_an_uncited_reference(self):
        results = [SimpleNamespace(stdout=json.dumps(item)) for item in (self.invalid, self.valid)]
        with patch("dossier.subprocess.run", side_effect=results) as run:
            result = dossier.generate_on_device("/test/model", self.evidence, self.ids)
        self.assertEqual(result["text"], self.valid["text"])
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
