"""Portable audit packages. Hashes prove consistency, not signer identity."""

import argparse
import base64
import hashlib
import json
from pathlib import Path

from domain import WorkflowError, initial_state, serialize
from evidence import MAX_FILE_BYTES, MAX_FILES, MAX_TOTAL_BYTES

FORMAT = "elo-audit-v2"


def digest(value):
    return hashlib.sha256(serialize(value).encode("utf-8")).hexdigest()


def verify_export(package):
    """Recompute every event and the terminal state without accessing a database."""
    try:
        if package["format"] not in {"elo-audit-v1", FORMAT}:
            return False
        keys = {"format", "state", "events", "manifest"}
        if package["format"] == FORMAT:
            keys.add("files")
        if set(package) != keys:
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
        expected = {"algorithm": "SHA-256", "event_count": len(events),
                    "last_event_hash": previous, "state_hash": state_hash}
        if package["format"] == "elo-audit-v1":
            # Historical v1 packages had no binary attachments.
            if state.get("attachments"):
                return False
        else:
            files = package["files"]
            if not isinstance(files, list) or len(files) > MAX_FILES:
                return False
            metadata = {item["id"]: item for item in state.get("attachments", [])}
            if len(metadata) != len(state.get("attachments", [])) or len(files) != len(metadata):
                return False
            sizes = [item["size"] for item in metadata.values()]
            if any(type(size) is not int or not 1 <= size <= MAX_FILE_BYTES for size in sizes) or sum(sizes) > MAX_TOTAL_BYTES:
                return False
            seen = set()
            for item in files:
                if set(item) != {"id", "content_base64"} or not isinstance(item["content_base64"], str) or len(item["content_base64"]) > ((MAX_FILE_BYTES + 2) // 3) * 4:
                    return False
                identifier = item["id"]
                if identifier in seen or identifier not in metadata:
                    return False
                seen.add(identifier)
                content = base64.b64decode(item["content_base64"], validate=True)
                if len(content) != metadata[identifier]["size"] or hashlib.sha256(content).hexdigest() != metadata[identifier]["sha256"]:
                    return False
            expected["files_hash"] = digest(files)
        return manifest == expected
    except (KeyError, TypeError, ValueError, AttributeError):
        return False


def build_export(snapshot):
    if not snapshot.get("audit_valid"):
        raise WorkflowError("A integridade da trilha precisa ser verificada antes da exportação.", 409)
    state = {key: value for key, value in snapshot.items()
             if key not in {"audit", "audit_valid", "ai_configured", "attachment_files"}}
    events = snapshot["audit"]
    files = snapshot.get("attachment_files", [])
    package = {
        "format": FORMAT, "state": state, "events": events, "files": files,
        "manifest": {"algorithm": "SHA-256", "event_count": len(events),
                     "last_event_hash": events[-1]["hash"] if events else "", "state_hash": digest(state),
                     "files_hash": digest(files)},
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
