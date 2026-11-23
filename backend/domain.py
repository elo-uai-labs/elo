"""The Elo demo workflow and transactional audit trail."""

import hashlib
import base64
import json
import re
from copy import deepcopy
import sqlite3
from contextlib import closing
from datetime import date, datetime, timezone
from pathlib import Path

DATASET = json.loads(Path(__file__).with_name("fixture.json").read_text(encoding="utf-8"))
IMPACTS = {
    "risk": ("Reavaliar exposição ao conflito de interesses", "Alta",
             "O vínculo qualificado envolve um aprovador do contrato. Verifique se a declaração de conflito e a segregação de funções cobriam esta contratação."),
    "maturity": ("Rever diligência de terceiros", "Em revisão",
                 "O cruzamento encontrou um vínculo cadastral a investigar. Avalie se a diligência de terceiros deveria identificar esse tipo de vínculo."),
}


class WorkflowError(Exception):
    def __init__(self, message, status=422):
        super().__init__(message)
        self.status = status


def serialize(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def required(data, key, limit=500):
    value = data.get(key)
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit:
        raise WorkflowError(f"Informe {key} com até {limit} caracteres.")
    return value.strip()


def choice(data, key, options):
    value = required(data, key, 32)
    if value not in options:
        raise WorkflowError(f"Valor inválido para {key}.")
    return value


def require(condition, message):
    if not condition:
        raise WorkflowError(message, 409)


def initial_state():
    return {
        "dataset": deepcopy(DATASET),
        "case": None,
        "risk": {
            "name": "Conflito de interesses em contratações", "level": "Moderada",
            "controls": ["Declaração de conflito de interesses", "Segregação de funções", "Diligência cadastral"],
        },
        "maturity": {"name": "Diligência de terceiros", "level": "Intermediária"},
        "actions": [],
    }


RULE = {"id": "contact-code-match", "name": "Vínculo cadastral com aprovador", "version": "1", "description": "Código cadastral não vazio e igual entre fornecedor e empregado aprovador do contrato. O vínculo é um indício, não comprovação de irregularidade."}

SUPPLIER_RULE = {"id": "supplier-shared-contact", "name": "Cadastro compartilhado entre fornecedores", "version": "1",
    "description": "O fornecedor do contrato compartilha código cadastral não vazio com outro fornecedor distinto. São possíveis cadastros administrativos comuns ou outras explicações legítimas; o sinal não comprova irregularidade.",
    "risk_rationale": "O código cadastral compartilhado por fornecedores exige revisão contextual da diligência cadastral e dos controles do risco associado. O sinal admite explicações legítimas e não comprova irregularidade.",
    "maturity_rationale": "Avalie se a diligência de terceiros da dimensão associada documenta e revisa códigos cadastrais compartilhados entre fornecedores. A metodologia permanece ilustrativa."}
REPEATED_RULE = {"id": "repeated-contract-profile", "name": "Contratos com perfil cadastral repetido", "version": "1", "experimental": True,
    "description": "Contratos distintos com mesmo fornecedor, aprovador e título após normalizar caixa e espaços. Não compara valor, data ou pagamento; recorrências legítimas são possíveis. Tipologia sintética experimental.",
    "risk_rationale": "Confira se contratos com perfil cadastral repetido correspondem a serviços recorrentes ou registros que precisam de revisão. Não há prova de duplicidade financeira ou irregularidade.",
    "maturity_rationale": "Revise a documentação da comparação de cadastros contratuais. A tipologia e a metodologia são ilustrativas."}
RULES = {RULE["id"]: RULE, SUPPLIER_RULE["id"]: SUPPLIER_RULE, REPEATED_RULE["id"]: REPEATED_RULE}


def validate_dataset(value):
    if not isinstance(value, dict) or set(value) != {"employees", "suppliers", "contracts"}:
        raise WorkflowError("Informe employees, suppliers e contracts na base sintética.")
    fields = {"employees": ("id", "name", "role", "contact_code"),
              "suppliers": ("id", "name", "contact_code"),
              "contracts": ("id", "supplier_id", "approver_id", "title")}
    prefixes = {"employees": "EMP-", "suppliers": "FOR-", "contracts": "CTR-"}
    clean = {}
    for table, keys in fields.items():
        rows = value[table]
        if not isinstance(rows, list) or len(rows) > 500:
            raise WorkflowError("Cada tabela aceita até 500 registros por importação.")
        clean[table] = []
        ids = set()
        for row in rows:
            if not isinstance(row, dict) or set(row) != set(keys):
                raise WorkflowError(f"Campos inválidos em {table}.")
            item = {}
            for key in keys:
                raw = row[key]
                if key == "contact_code" and raw == "":
                    item[key] = ""
                else:
                    item[key] = required(row, key, 160)
            identifier = item["id"]
            if not re.fullmatch(prefixes[table] + r"[A-Za-z0-9_-]{1,48}", identifier) or identifier in ids:
                raise WorkflowError(f"ID inválido ou duplicado em {table}.")
            ids.add(identifier)
            clean[table].append(item)
    if not any(clean.values()):
        raise WorkflowError("A importação precisa conter registros.")
    return clean


def normalize(state):
    if "cases" not in state:
        state["cases"] = [state["case"]] if state["case"] else []
    if "detection" not in state:
        state["detection"] = ({"status": "complete", "matches": len(state["cases"]),
                              "processed_contract_ids": [row["id"] for row in state["dataset"]["contracts"]],
                              "rule": RULE} if state["case"] else None)
    if state["detection"] is not None:
        state["detection"].setdefault("processed_by_rule", {RULE["id"]: list(state["detection"].get("processed_contract_ids", []))})
    state["case"] = state["cases"][0] if state["cases"] else None
    import governance
    import reporting
    state.setdefault("attachments", [])
    state.setdefault("scenarios", [])
    state.setdefault("integration_batches", [])
    state.setdefault("assistant_queries", [])
    state.setdefault("document_analyses", [])
    import work
    work.normalize(state)
    reporting.normalize(state)
    return governance.normalize(state)


def selected_case(state, case_id=None):
    cases = state.get("cases", [state["case"]] if state["case"] else [])
    if case_id is not None:
        if not isinstance(case_id, str):
            raise WorkflowError("case_id inválido.")
        case = next((item for item in cases if item["id"] == case_id), None)
        require(case is not None, "Caso não encontrado.")
        return case
    return cases[0] if cases else None


def presentation(state, case_id=None):
    result = normalize(deepcopy(state))
    result["case"] = selected_case(result, case_id)
    processed = (result["detection"] or {}).get("processed_by_rule", {})
    import rule_config
    result["rules"] = [{**rule_config.snapshot(result, identifier), "pending_count": sum(row["id"] not in processed.get(identifier, []) for row in result["dataset"]["contracts"]),
                       "completed": identifier in processed} for identifier, rule in RULES.items()]
    if result["case"]:
        import governance
        linked = governance.targets(result, result["case"])
        result["risk"], result["maturity"] = linked["risk"], linked["maturity"]
    return result


def match_cases(dataset):
    employees = {item["id"]: item for item in dataset["employees"]}
    suppliers = {item["id"]: item for item in dataset["suppliers"]}
    matches = []
    for contract in dataset["contracts"]:
        employee = employees[contract["approver_id"]]
        supplier = suppliers[contract["supplier_id"]]
        code = employee["contact_code"]
        if code and code == supplier["contact_code"]:
            matches.append({
                "id": "ELO-" + contract["id"].removeprefix("CTR-"), "status": "pending", "title": "Possível conflito de interesses",
                "evidence": [
                    {"id": contract["id"], "source": "Contratos sintéticos", "detail": f"{contract['title']}: fornecedor {supplier['id']} e aprovação por {employee['id']}."},
                    {"id": supplier["id"], "source": "Fornecedores sintéticos", "detail": f"{supplier['name']} possui o código cadastral {code}."},
                    {"id": employee["id"], "source": "Empregados sintéticos", "detail": f"{employee['name']} possui o código cadastral {code}."},
                ],
                "dossier": None, "decision": None, "impacts": [], "rule": deepcopy(RULE),
                "records": {"contract": deepcopy(contract), "supplier": deepcopy(supplier), "employee": deepcopy(employee)},
            })
    return matches


def match_supplier_cases(dataset):
    suppliers = {item["id"]: item for item in dataset["suppliers"]}
    grouped = {}
    for supplier in dataset["suppliers"]:
        if supplier["contact_code"]:
            grouped.setdefault(supplier["contact_code"], []).append(supplier["id"])
    matches = []
    for contract in dataset["contracts"]:
        supplier = suppliers[contract["supplier_id"]]
        code = supplier["contact_code"]
        others = sorted(identifier for identifier in grouped.get(code, []) if identifier != supplier["id"])
        if not others:
            continue
        other = suppliers[others[0]]
        matches.append({"id": "SIG-SUP-" + contract["id"], "title": SUPPLIER_RULE["name"], "status": "pending",
            "evidence": [
                {"id": contract["id"], "source": "Contratos sintéticos", "detail": f"{contract['title']}: contratação do fornecedor {supplier['id']}."},
                {"id": supplier["id"], "source": "Fornecedores sintéticos", "detail": f"{supplier['name']} possui o código cadastral {code}."},
                {"id": other["id"], "source": "Fornecedores sintéticos", "detail": f"{other['name']} possui o mesmo código cadastral {code}. O compartilhamento admite explicações legítimas e exige contexto."}],
            "dossier": None, "decision": None, "impacts": [], "rule": deepcopy(SUPPLIER_RULE),
            "records": {"contract": deepcopy(contract), "supplier": deepcopy(supplier), "related_supplier": deepcopy(other)}})
    return matches


def match_repeated_cases(dataset):
    """Exact identifiers and normalized title; never infer financial duplication."""
    suppliers = {row['id']: row for row in dataset['suppliers']}
    employees = {row['id']: row for row in dataset['employees']}
    groups = {}
    for row in dataset['contracts']:
        key = (row['supplier_id'], row['approver_id'], ' '.join(row['title'].split()).casefold())
        groups.setdefault(key, []).append(row)
    matches = []
    for group in groups.values():
        if len(group) < 2:
            continue
        ordered = sorted(group, key=lambda row: row['id'])
        for row in ordered:
            other = next(peer for peer in ordered if peer['id'] != row['id'])
            evidence = [{'id': item['id'], 'source': 'Contratos sintéticos',
                         'detail': f"{item['title']}: fornecedor {item['supplier_id']} e aprovação por {item['approver_id']}."}
                        for item in (row, other)]
            evidence.extend([
                {'id': row['supplier_id'], 'source': 'Fornecedores sintéticos', 'detail': suppliers[row['supplier_id']]['name']},
                {'id': row['approver_id'], 'source': 'Empregados sintéticos', 'detail': employees[row['approver_id']]['name']},
            ])
            matches.append({'id': 'SIG-REP-' + row['id'], 'title': REPEATED_RULE['name'], 'status': 'pending',
                            'evidence': evidence, 'dossier': None, 'decision': None, 'impacts': [],
                            'rule': deepcopy(REPEATED_RULE),
                            'records': {'contract': deepcopy(row), 'supplier': deepcopy(suppliers[row['supplier_id']]),
                                        'related_contract': deepcopy(other), 'employee': deepcopy(employees[row['approver_id']])}})
    return matches


def match_case(dataset):
    cases = match_cases(dataset)
    return cases[0] if cases else None


def transition(state, command, data):
    normalize(state)
    import governance
    import reporting
    import work
    if command in ("document/record", "evidence/review"):
        import document_analysis
        return document_analysis.record(state, data) if command == "document/record" else document_analysis.review(state, data)
    if command == "rule/config":
        import rule_config
        return rule_config.save(state, data)
    if command in work.COMMANDS:
        return work.transition(state, command, data)
    if command == "assistant/record":
        import consultation
        return consultation.record(state, data)
    if command == "integration/import":
        import monitoring
        return monitoring.transition(state, data)
    if command == "scenario/create":
        import insights
        return insights.simulate(state, data)
    if command in reporting.COMMANDS:
        return reporting.transition(state, command, data)
    if command == "evidence/upload":
        case = selected_case(state, data["case_id"])
        require(case is not None, "Caso não encontrado.")
        if data.get("action_id"):
            item = next((row for row in state["actions"] if row["id"] == data["action_id"] and row["case_id"] == case["id"]), None)
            require(item is not None, "Plano não pertence ao caso informado.")
            require(item["status"] not in ("done", "closure_requested"), "O plano está concluído ou aguardando revisão; não pode receber novos arquivos.")
        state["attachments"].append(data)
        return "Arquivo de evidência registrado", data["actor"], deepcopy(data)
    if command in governance.COMMANDS:
        return governance.transition(state, command, data)
    if command == "import":
        actor = required(data, "actor", 80)
        if data.get("synthetic") is not True:
            raise WorkflowError("Confirme que a base contém exclusivamente dados sintéticos.")
        incoming = validate_dataset(data.get("dataset"))
        merged = deepcopy(state["dataset"])
        for table, rows in incoming.items():
            existing = {item["id"] for item in merged[table]}
            if any(item["id"] in existing for item in rows):
                raise WorkflowError(f"A base já contém um dos IDs de {table}; use IDs novos.")
            if len(merged[table]) + len(rows) > 2000:
                raise WorkflowError("Limite local de 2000 registros por tabela atingido.")
            merged[table].extend(rows)
        employees = {row["id"] for row in merged["employees"]}
        suppliers = {row["id"] for row in merged["suppliers"]}
        if any(row["approver_id"] not in employees or row["supplier_id"] not in suppliers for row in merged["contracts"]):
            raise WorkflowError("Contrato contém referência a empregado ou fornecedor inexistente.")
        state["dataset"] = merged
        if incoming["suppliers"] and state["detection"] is not None:
            processed_by_rule = state["detection"].get("processed_by_rule", {})
            if SUPPLIER_RULE["id"] in processed_by_rule:
                processed_by_rule[SUPPLIER_RULE["id"]] = []
        if incoming["contracts"] and state["detection"] is not None:
            state["detection"].get("processed_by_rule", {}).pop(REPEATED_RULE["id"], None)
        return "Base sintética importada", actor, {"synthetic": True, "counts": {key: len(rows) for key, rows in incoming.items()},
            "record_ids": {key: [row["id"] for row in rows] for key, rows in incoming.items()}}
    if command == "detect":
        rule_id = choice(data, "rule_id", RULES) if "rule_id" in data else RULE["id"]
        import rule_config
        configuration = rule_config.get_config(state, rule_id)
        require(configuration["enabled"], "A regra está desativada. Revise os parâmetros antes de executar.")
        rule = rule_config.snapshot(state, rule_id)
        processed_by_rule = deepcopy((state["detection"] or {}).get("processed_by_rule", {}))
        processed = set(processed_by_rule.get(rule_id, []))
        pending = [row for row in state["dataset"]["contracts"] if row["id"] not in processed]
        require(rule_id not in processed_by_rule or pending, "A detecção já foi executada para todos os contratos desta regra. Importe novos registros.")
        known_ids = {item["id"] for item in state["cases"]}
        matches = [item for item in rule_config.match({**state["dataset"], "contracts": pending}, rule_id, configuration) if item["id"] not in known_ids]
        state["cases"].extend(matches)
        state["case"] = state["cases"][0] if state["cases"] else None
        processed_by_rule[rule_id] = [row["id"] for row in state["dataset"]["contracts"]]
        state["detection"] = {"status": "complete", "matches": len(state["cases"]), "rule": deepcopy(rule),
                              "processed_contract_ids": processed_by_rule.get(RULE["id"], []), "processed_by_rule": processed_by_rule}
        return "Indício detectado" if matches else "Análise concluída sem novos indícios", (required(data, "actor", 80) if data.get("actor") else "Regra de detecção"), {
            "system_component": "Regra de detecção", "case_ids": [item["id"] for item in matches], "case_id": matches[0]["id"] if matches else None,
            "contracts_analyzed": [row["id"] for row in pending], "rule": deepcopy(rule)}

    case = selected_case(state, data.get("case_id"))
    require(case is not None, "Execute a detecção primeiro.")
    case_id = case["id"]
    linked = governance.targets(state, case)
    if command == "dossier":
        initiator = required(data, "actor", 80) if data.get("actor") else "Serviço de síntese"
        data = {key: value for key, value in data.items() if key not in ("case_id", "actor")}
        require(case["decision"] is None, "A decisão já foi registrada.")
        revision = hashlib.sha256(serialize(data).encode("utf-8")).hexdigest()
        case["dossier"] = {**data, "revision": revision}
        return "Dossiê registrado", initiator, {"case_id": case_id, "system_component": "Serviço de síntese", **case["dossier"]}

    actor = required(data, "actor", 80)
    if command == "decision":
        require(case["dossier"] is not None, "Gere um dossiê antes da decisão.")
        require(case["decision"] is None, "A decisão já foi registrada.")
        if case.get("linkage") or "linkage_revision" in data:
            require(required(data, "linkage_revision", 64) == case["linkage_revision"], "Os vínculos mudaram. Atualize a página e revise o risco e a dimensão associados.")
        revision = required(data, "dossier_revision", 64)
        require(revision == case["dossier"]["revision"], "O dossiê mudou. Atualize a página e revise a nova versão.")
        outcome = choice(data, "outcome", ("discard", "monitor", "qualify"))
        review = choice(data, "review", ("accept", "adjust", "reject"))
        reason = required(data, "reason")
        case["decision"] = {"outcome": outcome, "review": review, "actor": actor, "reason": reason, "dossier_revision": revision}
        case["status"] = outcome
        if outcome == "qualify":
            require(not any(item["archived"] for item in linked.values()), "Os vínculos apontam para registros arquivados. Revise os vínculos antes de qualificar.")
            case["impacts"] = [
                {"kind": kind, "label": ("Reavaliar risco associado" if kind == "risk" else "Rever dimensão associada"), "status": "pending", "case_id": case_id,
                 "current_level": linked[kind]["level"], "proposed_level": ("Crítica" if kind == "risk" and linked[kind]["level"] == "Crítica" else level), "rationale": case.get("rule", {}).get(f"{kind}_rationale", rationale),
                 "target_id": linked[kind]["id"], "target_revision": linked[kind]["revision"],
                 "source_ids": [entry["id"] for entry in case["evidence"]]}
                for kind, (label, level, rationale) in IMPACTS.items()
            ]
        return "Decisão humana registrada", actor, {"case_id": case_id, **case["decision"], "suggestion": case["dossier"]["text"]}

    require(case["status"] == "qualify", "Qualifique uma fragilidade antes de continuar.")
    if command == "impact":
        kind = choice(data, "kind", IMPACTS)
        outcome = choice(data, "outcome", ("approved", "rejected"))
        impact = next(item for item in case["impacts"] if item["kind"] == kind)
        require(impact["status"] == "pending", "Esta proposta já foi decidida.")
        if outcome == "approved":
            require(not linked[kind]["archived"], "O registro associado foi arquivado.")
            if impact.get("target_revision"):
                require(linked[kind]["revision"] == impact["target_revision"], "A avaliação mudou desde a proposta. Recuse a proposta desatualizada e registre uma nova avaliação humana no catálogo.")
            require(linked[kind]["level"] in (impact["current_level"], impact["proposed_level"]),
                    "A avaliação mudou desde a proposta. Revise o contexto antes de aprovar.")
        impact.update(status=outcome, actor=actor, reason=required(data, "reason"))
        if outcome == "approved":
            linked[kind]["level"] = impact["proposed_level"]
            governance.stamp(linked[kind])
        return "Impacto avaliado", actor, {"case_id": case_id, **impact}

    if command == "action":
        due = required(data, "due", 10)
        try:
            if date.fromisoformat(due).isoformat() != due:
                raise ValueError
        except ValueError as error:
            raise WorkflowError("Informe um prazo válido (AAAA-MM-DD).") from error
        item = {
            "id": f"REC-{len(state['actions']) + 1:03}", "title": required(data, "title", 160),
            "actor": actor, "owner": required(data, "owner", 80), "due": due,
            "status": "open", "evidence": "", "case_id": case_id,
        }
        state["actions"].append(item)
        return "Recomendação criada", actor, item

    return governance.action_transition(state, command, data, case)


class Store:
    def __init__(self, path):
        self.path = path
        with closing(self.connect()) as db, db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS workflow (id INTEGER PRIMARY KEY CHECK (id = 1), value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS audit (seq INTEGER PRIMARY KEY, event TEXT NOT NULL, hash TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS evidence_files (id TEXT PRIMARY KEY, content BLOB NOT NULL);
                CREATE TRIGGER IF NOT EXISTS evidence_no_update BEFORE UPDATE ON evidence_files
                    BEGIN SELECT RAISE(ABORT, 'append-only'); END;
                CREATE TRIGGER IF NOT EXISTS evidence_no_delete BEFORE DELETE ON evidence_files
                    BEGIN SELECT RAISE(ABORT, 'append-only'); END;
                CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit
                    BEGIN SELECT RAISE(ABORT, 'append-only'); END;
                CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit
                    BEGIN SELECT RAISE(ABORT, 'append-only'); END;
            """)
            db.execute("INSERT OR IGNORE INTO workflow VALUES (1, ?)", (serialize(initial_state()),))

    def connect(self):
        return sqlite3.connect(self.path, timeout=5)

    def read(self, case_id=None):
        with closing(self.connect()) as db:
            db.execute("BEGIN")
            return presentation(self.snapshot(db), case_id)

    def export_state(self, include_files=False):
        with closing(self.connect()) as db:
            db.execute("BEGIN")
            state = self.snapshot(db)
            if include_files:
                require(state["audit_valid"], "A integridade da trilha e dos arquivos precisa ser verificada.")
                state["attachment_files"] = [{"id": identifier, "content_base64": base64.b64encode(content).decode("ascii")}
                    for identifier, content in db.execute("SELECT id, content FROM evidence_files ORDER BY id")]
            return state

    def evidence_file(self, identifier):
        with closing(self.connect()) as db:
            db.execute("BEGIN")
            state = self.snapshot(db)
            require(state["audit_valid"], "A integridade da trilha e dos arquivos precisa ser verificada.")
            metadata = next((row for row in state.get("attachments", []) if row["id"] == identifier), None)
            if metadata is None:
                raise WorkflowError("Arquivo não encontrado.", 404)
            return metadata, bytes(db.execute("SELECT content FROM evidence_files WHERE id = ?", (identifier,)).fetchone()[0])

    def apply(self, command, data, authorize=None):
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            state = self.snapshot(db)
            require(state.pop("audit_valid"), "A integridade da trilha precisa ser verificada.")
            audit = state.pop("audit")
            authentication = authorize(state) if authorize else {"mode": "local-demo"}
            transition_data = data
            if command == "evidence/upload":
                from evidence import MAX_FILES, MAX_TOTAL_BYTES, validate_upload
                metadata, content = validate_upload(data)
                count, used = db.execute("SELECT COUNT(*), COALESCE(SUM(length(content)), 0) FROM evidence_files").fetchone()
                require(count < MAX_FILES and used + len(content) <= MAX_TOTAL_BYTES,
                        "Limite local de 200 arquivos ou 20 MiB atingido.")
                metadata["id"] = f"EVD-{count + 1:04}"
                db.execute("INSERT INTO evidence_files (id, content) VALUES (?, ?)", (metadata["id"], content))
                transition_data = metadata
            action, actor, detail = transition(state, command, transition_data)
            normalize(state)
            state_encoded = serialize(state)
            event = {
                "seq": len(audit) + 1, "at": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                "action": action, "actor": actor, "details": detail,
                "authentication": authentication,
                "previous_hash": audit[-1]["hash"] if audit else "",
                "state_hash": hashlib.sha256(state_encoded.encode("utf-8")).hexdigest(),
            }
            encoded = serialize(event)
            digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
            db.execute("INSERT INTO audit VALUES (?, ?, ?)", (event["seq"], encoded, digest))
            db.execute("UPDATE workflow SET value = ? WHERE id = 1", (state_encoded,))
            return presentation({**state, "audit": [*audit, {**event, "hash": digest}], "audit_valid": True}, data.get("case_id"))

    @staticmethod
    def snapshot(db):
        try:
            state = json.loads(db.execute("SELECT value FROM workflow WHERE id = 1").fetchone()[0])
            audit = []
            previous = ""
            valid = True
            for seq, encoded, digest in db.execute("SELECT seq, event, hash FROM audit ORDER BY seq"):
                event = json.loads(encoded)
                valid &= seq == len(audit) + 1 == event["seq"] and event["previous_hash"] == previous
                valid &= hashlib.sha256(encoded.encode("utf-8")).hexdigest() == digest
                audit.append({**event, "hash": digest})
                previous = digest
            if audit:
                valid &= audit[-1]["state_hash"] == hashlib.sha256(serialize(state).encode("utf-8")).hexdigest()
            else:
                valid &= state == initial_state()
            files = {identifier: content for identifier, content in db.execute("SELECT id, content FROM evidence_files")}
            attachments = state.get("attachments", [])
            valid &= len(attachments) == len(files) and {item["id"] for item in attachments} == set(files)
            for item in attachments:
                content = files.get(item["id"])
                valid &= isinstance(content, bytes) and len(content) == item["size"] and hashlib.sha256(content).hexdigest() == item["sha256"]
            return {**state, "audit": audit, "audit_valid": bool(valid)}
        except (ValueError, KeyError, TypeError) as error:
            raise WorkflowError("A trilha contém registros inválidos.", 503) from error
