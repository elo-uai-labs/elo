"""Reproducible evaluation of planted signals, independent of the workflow store."""

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path

from domain import RULE, WorkflowError, match_cases, serialize, validate_dataset

FIXTURE_PATH = Path(__file__).with_name("lab_fixture.json")


def load_fixture():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def validated_fixture(fixture):
    """Check label coverage without deriving any label from the detector rule."""
    try:
        if fixture["synthetic"] is not True:
            raise ValueError("O laboratório exige dados sintéticos.")
        if not all(isinstance(fixture[key], str) and fixture[key].strip()
                   for key in ("id", "version", "description")):
            raise ValueError("Identificação e versão do laboratório são obrigatórias.")
        if fixture["expected_rule"] != {key: RULE[key] for key in ("id", "version")}:
            raise ValueError("O gabarito não corresponde à versão da regra avaliada.")
        dataset = validate_dataset(fixture["dataset"])
        contracts = [row["id"] for row in dataset["contracts"]]
        employees = {row["id"] for row in dataset["employees"]}
        suppliers = {row["id"] for row in dataset["suppliers"]}
        if any(row["approver_id"] not in employees or row["supplier_id"] not in suppliers
               for row in dataset["contracts"]):
            raise ValueError("O laboratório contém referências inexistentes.")
        expected = fixture["expected_contract_ids"]
        if not isinstance(expected, list) or any(not isinstance(item, str) for item in expected):
            raise ValueError("O gabarito deve listar IDs de contratos.")
        if len(set(expected)) != len(expected) or not set(expected).issubset(contracts):
            raise ValueError("O gabarito contém contratos duplicados ou inexistentes.")
        scenarios = fixture["scenarios"]
        if not isinstance(scenarios, list) or any(
            not isinstance(row, dict) or any(not isinstance(row.get(key), str) or not row[key].strip()
                for key in ("contract_id", "scenario", "reason")) for row in scenarios
        ):
            raise ValueError("Cada cenário precisa de contrato, descrição e justificativa.")
        scenario_ids = [row["contract_id"] for row in scenarios]
        if len(set(scenario_ids)) != len(scenario_ids) or set(scenario_ids) != set(contracts):
            raise ValueError("Os cenários precisam cobrir cada contrato exatamente uma vez.")
        return dataset, set(expected), {row["contract_id"]: row for row in scenarios}
    except (KeyError, TypeError, WorkflowError) as error:
        raise ValueError("Fixture do laboratório inválida.") from error


def evaluate_predictions(fixture, detected_contract_ids):
    """Compare predictions against explicit, manually authored fixture labels."""
    dataset, expected, scenarios = validated_fixture(fixture)
    contract_ids = [row["id"] for row in dataset["contracts"]]
    predictions = list(detected_contract_ids)
    if any(not isinstance(item, str) for item in predictions):
        raise ValueError("A detecção deve retornar IDs de contratos.")
    if len(set(predictions)) != len(predictions) or not set(predictions).issubset(contract_ids):
        raise ValueError("A detecção retornou contratos duplicados ou fora do laboratório.")
    predicted = set(predictions)
    outcomes = []
    counts = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    for contract_id in contract_ids:
        positive, detected = contract_id in expected, contract_id in predicted
        outcome = ("tp" if detected else "fn") if positive else ("fp" if detected else "tn")
        counts[outcome] += 1
        outcomes.append({**scenarios[contract_id], "expected_signal": positive,
                         "detected_signal": detected, "outcome": outcome})

    def ratio(numerator, denominator):
        return {"value": numerator / denominator if denominator else None,
                "numerator": numerator, "denominator": denominator}

    return {
        "fixture": {"id": fixture["id"], "version": fixture["version"],
                    "sha256": hashlib.sha256(serialize(fixture).encode("utf-8")).hexdigest()},
        "rule": deepcopy(RULE), "unit": "contract",
        "scope": "Laboratório sintético: sinais plantados, sem conclusão de culpa. Resultados não estimam desempenho em dados reais.",
        "counts": {"total": len(contract_ids), "expected_positive": len(expected),
                   "predicted_positive": len(predicted), **counts},
        "metrics": {"precision": ratio(counts["tp"], counts["tp"] + counts["fp"]),
                    "recall": ratio(counts["tp"], counts["tp"] + counts["fn"])},
        "outcomes": outcomes,
    }


def run_laboratory(fixture=None, detector=None):
    fixture = deepcopy(load_fixture() if fixture is None else fixture)
    dataset, _, _ = validated_fixture(fixture)
    cases = (match_cases if detector is None else detector)(deepcopy(dataset))
    try:
        contract_ids = [case["records"]["contract"]["id"] for case in cases]
    except (KeyError, TypeError) as error:
        raise ValueError("A detecção não identificou os contratos dos sinais.") from error
    return evaluate_predictions(fixture, contract_ids)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Grava o resultado JSON neste arquivo novo, sem sobrescrever arquivos existentes.")
    args = parser.parse_args()
    try:
        encoded = json.dumps(run_laboratory(), ensure_ascii=False, indent=2) + "\n"
        if args.output:
            with args.output.open("x", encoding="utf-8") as target:
                target.write(encoded)
        else:
            print(encoded, end="")
    except (OSError, ValueError) as error:
        parser.exit(1, f"Laboratório não concluído: {error}\n")


if __name__ == "__main__":
    main()
