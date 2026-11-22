"""Portable audit packages. Hashes prove consistency, not signer identity."""

import argparse
import hashlib
import json
from pathlib import Path

from domain import WorkflowError, initial_state, serialize

FORMAT = "elo-audit-v1"


def digest(value):
    return hashlib.sha256(serialize(value).encode("utf-8")).hexdigest()


def verify_export(package):
    """Recompute every event and the terminal state without accessing a database."""
    try:
        if package["format"] != FORMAT:
            return False
        state, events = package["state"], package["events"]
        manifest = package["manifest"]
        if not isinstance(state, dict) or not isinstance(events, list):
            return False
        previous = ""
        for sequence, entry in enumerate(events, 1):
            event = {key: value for key, value in entry.items() if key != "hash"}
            if event["seq"] != sequence or event["previous_hash"] != previous or digest(event) != entry["hash"]:
                return False
            previous = entry["hash"]
        state_hash = digest(state)
        if events:
            if events[-1]["state_hash"] != state_hash:
                return False
        elif state != initial_state():
            return False
        return manifest == {"algorithm": "SHA-256", "event_count": len(events),
                            "last_event_hash": previous, "state_hash": state_hash}
    except (KeyError, TypeError, ValueError, AttributeError):
        return False


def build_export(snapshot):
    if not snapshot.get("audit_valid"):
        raise WorkflowError("A integridade da trilha precisa ser verificada antes da exportação.", 409)
    state = {key: value for key, value in snapshot.items()
             if key not in {"audit", "audit_valid", "ai_configured"}}
    events = snapshot["audit"]
    package = {
        "format": FORMAT, "state": state, "events": events,
        "manifest": {"algorithm": "SHA-256", "event_count": len(events),
                     "last_event_hash": events[-1]["hash"] if events else "", "state_hash": digest(state)},
    }
    if not verify_export(package):
        raise WorkflowError("O pacote de auditoria não passou na verificação independente.", 409)
    return package


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verifica a consistência de um pacote Elo; não atesta autoria externa.")
    parser.add_argument("package", type=Path)
    args = parser.parse_args()
    try:
        valid = verify_export(json.loads(args.package.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        valid = False
    print("Pacote íntegro (hashes, encadeamento e estado)." if valid else "Pacote inválido.")
    raise SystemExit(0 if valid else 1)
