import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from domain import match_cases
from laboratory import evaluate_predictions, load_fixture, run_laboratory


class LaboratoryTest(unittest.TestCase):
    def test_fixed_ground_truth_and_repeatability(self):
        fixture = load_fixture()
        original = copy.deepcopy(fixture)
        report = run_laboratory(fixture)
        self.assertEqual(report, run_laboratory(fixture))
        self.assertEqual(fixture, original)
        self.assertEqual(report["counts"], {"total": 8, "expected_positive": 2,
            "predicted_positive": 2, "tp": 2, "fp": 0, "fn": 0, "tn": 6})
        self.assertEqual(report["metrics"]["precision"], {"value": 1, "numerator": 2, "denominator": 2})
        self.assertEqual(report["metrics"]["recall"], {"value": 1, "numerator": 2, "denominator": 2})
        outcomes = {row["contract_id"]: row for row in report["outcomes"]}
        for identifier in ("CTR-LAB-EMPTY-BOTH", "CTR-LAB-NONAPPROVER", "CTR-LAB-DIFFERENT",
                           "CTR-LAB-EMPTY-EMP", "CTR-LAB-EMPTY-SUP", "CTR-LAB-OTHER-APPROVER"):
            self.assertEqual(outcomes[identifier]["outcome"], "tn")

    def test_mutated_detector_exposes_false_positive_and_false_negative(self):
        def faulty_detector(dataset):
            cases = match_cases(dataset)
            cases.pop()  # Miss the manually labeled Beta positive.
            cases.append({"records": {"contract": {"id": "CTR-LAB-NONAPPROVER"}}})
            return cases

        report = run_laboratory(detector=faulty_detector)
        self.assertEqual(report["counts"], {"total": 8, "expected_positive": 2,
            "predicted_positive": 2, "tp": 1, "fp": 1, "fn": 1, "tn": 5})
        self.assertEqual(report["metrics"]["precision"]["value"], .5)
        self.assertEqual(report["metrics"]["recall"]["value"], .5)

    def test_zero_denominators_are_explicit_not_perfect_scores(self):
        report = run_laboratory(detector=lambda dataset: [])
        self.assertEqual(report["metrics"]["precision"], {"value": None, "numerator": 0, "denominator": 0})
        self.assertEqual(report["metrics"]["recall"]["value"], 0)
        fixture = load_fixture()
        fixture["expected_contract_ids"] = []
        report = evaluate_predictions(fixture, [])
        self.assertIsNone(report["metrics"]["recall"]["value"])
        self.assertEqual(report["counts"]["tn"], 8)

    def test_labels_are_not_recomputed_from_changed_data(self):
        fixture = load_fixture()
        fixture["dataset"]["employees"][0]["contact_code"] = "FICT-CHANGED"
        report = run_laboratory(fixture)
        self.assertEqual(report["counts"]["expected_positive"], 2)
        self.assertEqual(report["counts"]["fn"], 1)
        self.assertNotEqual(report["fixture"]["sha256"], run_laboratory()["fixture"]["sha256"])

    def test_invalid_labels_or_detector_outputs_are_rejected(self):
        for mutate in (
            lambda f: f["expected_contract_ids"].append("CTR-MISSING"),
            lambda f: f["expected_contract_ids"].append("CTR-LAB-POS-A"),
            lambda f: f["scenarios"].pop(),
            lambda f: f["expected_rule"].update(version="unknown"),
            lambda f: f["dataset"]["contracts"][0].update(approver_id="EMP-MISSING"),
        ):
            fixture = load_fixture()
            mutate(fixture)
            with self.assertRaises(ValueError):
                run_laboratory(fixture)
        for predictions in (["CTR-UNKNOWN"], ["CTR-LAB-POS-A", "CTR-LAB-POS-A"], [None]):
            with self.assertRaises(ValueError):
                evaluate_predictions(load_fixture(), predictions)


if __name__ == "__main__":
    unittest.main()
