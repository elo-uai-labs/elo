"""Explainable local connections, institutional memory, trends and simulations."""

from copy import deepcopy
from datetime import datetime
from zoneinfo import ZoneInfo

from domain import WorkflowError, required, require, selected_case


def connections(state, case_id=None):
    case = selected_case(state, case_id)
    require(case is not None, "Selecione um caso para consultar suas conexões.")
    nodes, edges = {}, []

    def node(identifier, kind, label):
        nodes[identifier] = {"id": identifier, "kind": kind, "label": label}

    def edge(source, target, relation):
        edges.append({"source": source, "target": target, "relation": relation})

    node(case["id"], "case", case["id"])
    risk = next(item for item in state["risks"] if item["id"] == case["risk_id"])
    dimension = next(item for item in state["dimensions"] if item["id"] == case["dimension_id"])
    for item, kind in ((risk, "risk"), (dimension, "maturity")):
        node(item["id"], kind, item["name"])
        edge(case["id"], item["id"], "vínculo registrado; impactos exigem decisão humana")
    for control in state["controls"]:
        if control["id"] in risk["control_ids"]:
            node(control["id"], "control", control["name"])
            edge(risk["id"], control["id"], "controle vinculado")
    for source in case["evidence"]:
        node(source["id"], "source", source["source"])
        edge(source["id"], case["id"], "fonte do indício")
    for action in state["actions"]:
        if action["case_id"] == case["id"]:
            node(action["id"], "action", action["title"])
            edge(case["id"], action["id"], "recomendação e plano de tratamento")
    for attachment in state.get("attachments", []):
        if attachment["case_id"] == case["id"]:
            node(attachment["id"], "attachment", attachment["name"])
            edge(attachment["id"], attachment.get("action_id") or case["id"], "arquivo de evidência")
    for proposal in case.get("impacts", []):
        identifier = f"IMP-{case['id']}-{proposal['kind']}"
        status = {"pending": "Pendente", "approved": "Aprovado", "rejected": "Recusado"}[proposal["status"]]
        node(identifier, "impact", f"{proposal['label']} · {status}")
        edge(case["id"], identifier, "proposta de impacto")
        edge(identifier, proposal.get("target_id") or (risk["id"] if proposal["kind"] == "risk" else dimension["id"]), status)
    for report in state.get("reports", []):
        if case["id"] in report["case_ids"]:
            node(report["id"], "report", report["title"])
            edge(case["id"], report["id"], "incluído no relatório; consulte seu estado de revisão")
    for scenario in state.get("scenarios", []):
        if scenario["risk_id"] == risk["id"]:
            node(scenario["id"], "scenario", f"Cenário hipotético: {scenario['hypothetical_level']}")
            edge(risk["id"], scenario["id"], "simulação sem alteração da avaliação vigente")
    for assessment in state.get("assessments", []):
        if assessment["dimension_id"] == dimension["id"]:
            node(assessment["id"], "assessment", f"Avaliação {assessment['score']}%")
            edge(dimension["id"], assessment["id"], "histórico de avaliação da dimensão")
    if case.get("decision"):
        identifier = f"DEC-{case['id']}"
        node(identifier, "decision", f"{case['decision']['actor']} · {case['decision']['outcome']}")
        edge(case["id"], identifier, "decisão humana registrada")
    return {"case_id": case["id"], "nodes": list(nodes.values()), "edges": edges,
            "scope": "Conexões registradas no ambiente local. Vínculo não comprova irregularidade; propostas não são impactos aprovados."}


def similar_cases(state, case_id=None):
    current = selected_case(state, case_id)
    require(current is not None, "Selecione um caso para consultar a memória institucional.")
    results = []
    current_sources = {item["id"] for item in current["evidence"]}
    for case in state["cases"]:
        if case["id"] == current["id"] or not case.get("decision"):
            continue
        reasons, score = [], 0
        shared = sorted(current_sources & {item["id"] for item in case["evidence"]})
        if shared:
            reasons.append("Fontes compartilhadas: " + ", ".join(shared))
            score += 3
        for key, label in (("risk_id", "Mesmo risco"), ("dimension_id", "Mesma dimensão")):
            if current.get(key) and current.get(key) == case.get(key):
                reasons.append(label)
                score += 1
        if current.get("rule", {}).get("id") == case.get("rule", {}).get("id") and current.get("rule"):
            reasons.append("Mesma regra de identificação")
            score += 1
        if score:
            results.append({"case_id": case["id"], "score": score, "reasons": reasons,
                            "decision": deepcopy(case["decision"]), "shared_sources": shared})
    return {"case_id": current["id"], "matches": sorted(results, key=lambda row: (-row["score"], row["case_id"]))[:5],
            "methodology": "Ordenação explicável: fonte compartilhada +3; mesmo risco, dimensão ou regra +1 cada. Apenas casos com decisão humana; até cinco resultados. Similaridade não impõe uma decisão."}


def trends(state):
    require(state.get("audit_valid"), "Verifique a integridade antes de consultar tendências.")
    periods = {}
    action_statuses = {}
    for event in state.get("audit", []):
        try:
            period = datetime.fromisoformat(event["at"]).astimezone(ZoneInfo("America/Sao_Paulo")).strftime("%Y-%m")
        except (ValueError, TypeError, KeyError) as error:
            raise WorkflowError("Há evento sem data válida para compor a tendência.", 409) from error
        bucket = periods.setdefault(period, {"period": period, "detected": 0, "qualified": 0, "monitored": 0, "discarded": 0, "completed": 0})
        details = event.get("details", {})
        if event["action"] in {"Indício detectado", "Integração sintética executada"}:
            bucket["detected"] += len(details.get("case_ids", [details["case_id"]] if details.get("case_id") else []))
        elif event["action"] == "Decisão humana registrada":
            key = {"qualify": "qualified", "monitor": "monitored", "discard": "discarded"}.get(details.get("outcome"))
            if key:
                bucket[key] += 1
        if event["action"] in {"Recomendação criada", "Recomendação atualizada", "Encerramento solicitado", "Encerramento revisado", "Plano de ação editado"} and details.get("id"):
            identifier = details["id"]
            if details.get("status") == "done" and action_statuses.get(identifier) != "done":
                bucket["completed"] += 1
            action_statuses[identifier] = details.get("status")
    return {"timezone": "America/Sao_Paulo", "periods": [periods[key] for key in sorted(periods)],
            "scope": "Contagens de eventos por mês; não medem prevalência de irregularidades nem benefício operacional. Períodos e volumes de importação podem não ser comparáveis."}


def simulate(state, data):
    actor, reason = required(data, "actor", 80), required(data, "reason")
    risk_id = required(data, "risk_id", 32)
    risk = next((item for item in state["risks"] if item["id"] == risk_id), None)
    require(risk is not None and not risk["archived"], "Selecione um risco ativo.")
    require(required(data, "risk_revision", 64) == risk["revision"], "O risco mudou. Revise o cenário com a versão atual.")
    likelihood, impact = data.get("likelihood"), data.get("impact")
    if any(type(value) is not int or not 1 <= value <= 5 for value in (likelihood, impact)):
        raise WorkflowError("Probabilidade e impacto devem ser inteiros de 1 a 5.")
    score = likelihood * impact
    level = "Baixa" if score <= 4 else "Moderada" if score <= 9 else "Alta" if score <= 16 else "Crítica"
    scenarios = state.setdefault("scenarios", [])
    require(len(scenarios) < 200, "Limite local de 200 cenários atingido.")
    scenario = {"id": f"SIM-{len(scenarios)+1:03}", "actor": actor, "reason": reason,
                "risk_id": risk_id, "risk_revision": risk["revision"], "current_level": risk["level"],
                "likelihood": likelihood, "impact": impact, "score": score, "hypothetical_level": level,
                "methodology": "Matriz ilustrativa elo-scenario-v1: probabilidade × impacto; 1–4 Baixa, 5–9 Moderada, 10–16 Alta, 17–25 Crítica. Não é metodologia oficial da CAIXA.",
                "effect": "Simulação registrada; a avaliação vigente do risco não foi alterada."}
    scenarios.append(scenario)
    return "Cenário simulado", actor, deepcopy(scenario)
