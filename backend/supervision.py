"""Descriptive supervision measures; never decisions about a reviewer."""

from datetime import datetime

from domain import WorkflowError


def summary(snapshot):
    if not snapshot.get("audit_valid"):
        raise WorkflowError("Verifique a integridade da trilha antes de calcular a supervisão.", 409)
    cases = snapshot.get("cases", [snapshot["case"]] if snapshot.get("case") else [])
    groups = []
    for mode in ("real", "local"):
        reviewed = [case for case in cases if case.get("decision") and case.get("dossier", {}).get("mode") == mode]
        counts = {review: sum(case["decision"]["review"] == review for case in reviewed)
                  for review in ("accept", "adjust", "reject")}
        groups.append({"mode": mode, "reviewed": len(reviewed), **counts,
                       "agreement_rate": counts["accept"] / len(reviewed) if reviewed else None,
                       "disagreements": [{"case_id": case["id"], **case["decision"]}
                                         for case in reviewed if case["decision"]["review"] != "accept"]})
    # Use server-recorded events, not a self-declared review duration.
    dossiers, decisions = {}, []
    for event in snapshot.get("audit", []):
        details = event.get("details", {})
        case_id = details.get("case_id")
        if event["action"] == "Dossiê registrado":
            dossiers[(case_id, details.get("revision"))] = event["at"]
        elif event["action"] == "Decisão humana registrada":
            started = dossiers.get((case_id, details.get("dossier_revision")))
            seconds = None
            if started:
                try:
                    seconds = (datetime.fromisoformat(event["at"]) - datetime.fromisoformat(started)).total_seconds()
                except (ValueError, TypeError):
                    pass
            decisions.append({"case_id": case_id, "actor": event["actor"], "review": details.get("review"),
                              "seconds": seconds, "seq": event["seq"],
                              "identity_mode": "local-auth" if event.get("authentication", {}).get("mode") == "local-auth" else "local-demo"})
    # A transparent screening rule for a human to inspect, never a finding.
    reviewers = {}
    for decision in decisions:
        reviewers.setdefault((decision["actor"], decision["identity_mode"]), []).append(decision)
    alerts = []
    for (actor, identity_mode), items in reviewers.items():
        recent = items[-5:]
        if len(recent) == 5 and all(item["review"] == "accept" and item["seconds"] is not None
                                   and 0 <= item["seconds"] < 10 for item in recent):
            alerts.append({"actor": actor, "identity_mode": identity_mode, "case_ids": [item["case_id"] for item in recent],
                           "rule": "five-fast-accepts-v1",
                           "reason": "As últimas cinco revisões aceitaram a sugestão em menos de 10 segundos após o registro do dossiê. Verifique o contexto da supervisão; isso não comprova aprovação automática."})
    review_events = [event for event in snapshot.get("audit", []) if event["action"] == "Decisão humana registrada"]
    authenticated = sum(event.get("authentication", {}).get("mode") == "local-auth" for event in review_events)
    return {"groups": groups, "pending": sum(not case.get("decision") for case in cases),
            "total_cases": len(cases), "alerts": alerts,
            "identity_counts": {"authenticated_decisions": authenticated,
                                "legacy_or_declared_decisions": len(review_events) - authenticated},
            "methodology": "Concordância = aceitações / revisões registradas, separadas entre IA real e síntese local. Sem revisões, a taxa não é calculada. A heurística sinaliza as últimas cinco aceitações de um responsável, todas em menos de 10 segundos após o dossiê; tempo decorrido não mede atenção nem comprova automação.",
            "identity_scope": "A origem da identidade é preservada por evento. Registros sem autenticação explícita são autodeclarados ou de serviço local; ativar login não autentica retroativamente o histórico."}
