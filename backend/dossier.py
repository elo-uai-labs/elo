"""Summarize synthetic evidence without granting decision authority."""

import json
import logging
import os
import re
import subprocess
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

from domain import WorkflowError

PROMPT_VERSION = "elo-dossier-v4"
INSTRUCTIONS = (
    "Redija uma síntese curta de evidências sintéticas de um indício de integridade em contratações. "
    "Use apenas as evidências recebidas. Associe a cada afirmação os IDs de suas fontes em source_ids. "
    "Explique a coincidência e sua limitação, e sugira somente uma verificação humana. "
    "Nunca atribua culpa, confirme uma irregularidade, proponha penalidade ou decida o caso."
)


def configured():
    return bool(os.getenv("ELO_ON_DEVICE_BIN") or (os.getenv("OPENAI_API_KEY") and os.getenv("ELO_MODEL")))


def verified_dossier(output, model, ids):
    claims = output["claims"]
    limitations = output["limitations"].strip()
    suggestion = output["suggestion"].strip()
    if not isinstance(claims, list) or not 1 <= len(claims) <= 6 or not limitations or not suggestion:
        raise ValueError("Invalid dossier shape")
    clean = []
    references = []
    for claim in claims:
        text = claim["text"].strip()
        sources = claim["source_ids"]
        if not text or not isinstance(sources, list) or not sources:
            raise ValueError("Each factual claim needs sources")
        if any(not isinstance(ref, str) or ref not in ids for ref in sources):
            raise ValueError("Invalid claim source IDs")
        mentioned = set(re.findall(r"\b(?:CTR|FOR|EMP)-[A-Za-z0-9_-]+", text))
        if not mentioned.issubset(ids):
            raise ValueError("Every mentioned record must exist in the supplied evidence")
        clean.append({"text": text, "source_ids": list(dict.fromkeys(sources))})
        references.extend(sources)
    text = " ".join([claim["text"] for claim in clean] + [limitations, suggestion])
    if len(text) > 2400 or not isinstance(model, str) or not model.strip():
        raise ValueError("Invalid dossier size or model")
    return {"text": text, "source_ids": list(dict.fromkeys(references)), "claims": clean,
            "limitations": limitations, "suggestion": suggestion,
            "mode": "real", "model": model, "prompt_version": PROMPT_VERSION}


def generate_on_device(binary, evidence, ids):
    citation_contract = (
        " Os únicos IDs de fontes permitidos são: " + ", ".join(ids) + ". "
        "Retorne de uma a seis afirmações factuais em claims, cada uma com text e source_ids. "
        "source_ids deve conter somente IDs recebidos que sustentam a mesma afirmação; a interface os mostra junto ao texto. "
        "Separe limitations (limitações da análise) e suggestion (próxima verificação humana). "
        "Não use nomes de pessoas ou tabelas como identificadores de fonte."
    )
    payload = {"instructions": INSTRUCTIONS + citation_contract, "evidence": json.dumps(evidence, ensure_ascii=False)}
    environment = {name: os.environ[name] for name in ("HOME", "PATH", "TMPDIR", "LANG", "LC_ALL") if name in os.environ}
    deadline = time.monotonic() + 45
    try:
        for attempt in range(2):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(binary, 45)
            process = subprocess.run([binary], input=json.dumps(payload), capture_output=True, text=True, check=True, timeout=remaining, env=environment)
            try:
                output = json.loads(process.stdout)
                return verified_dossier(output, output["model"], ids)
            except (ValueError, KeyError, TypeError, AttributeError):
                if attempt:
                    raise
                # A model can list a source it forgot to cite. Regenerate once;
                # never patch its factual text or silently drop invalid references.
                payload["instructions"] += (
                    " Sua resposta anterior foi rejeitada pela validação de formato ou referências. "
                    "Gere uma nova síntese curta com source_ids próprios para cada afirmação e declare somente "
                    "identificadores de fontes existentes recebidas na entrada."
                )
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError, AttributeError) as error:
        logging.getLogger(__name__).warning("Falha do dossiê Apple: %s", str(error) if isinstance(error, ValueError) else type(error).__name__)
        raise WorkflowError("A síntese por IA no dispositivo não foi concluída. Confira o modelo local e tente novamente.", 502) from error


def generate(evidence, mode, rule_id="contact-code-match"):
    ids = [item["id"] for item in evidence]
    if mode == "local" and rule_id == "supplier-shared-contact":
        output = {
            "claims": [{"text": item["detail"], "source_ids": [item["id"]]} for item in evidence],
            "limitations": "Fornecedores podem compartilhar dados cadastrais por razões legítimas. A coincidência isolada não comprova irregularidade.",
            "suggestion": "Verifique a origem e a atualização dos cadastros e a diligência aplicada aos fornecedores.",
        }
        return {**verified_dossier(output, "regra-local", ids), "mode": "local"}
    if mode == "local":
        contract, supplier, employee = ids
        output = {
            "claims": [
                {"text": f"O contrato {contract} relaciona o fornecedor {supplier} ao empregado {employee} como aprovador.", "source_ids": ids},
                {"text": f"Os registros {supplier} e {employee} têm o mesmo código cadastral.", "source_ids": [supplier, employee]},
            ],
            "limitations": "A coincidência isolada não comprova irregularidade.",
            "suggestion": "Sugestão: verificar a origem e a validade do vínculo antes de concluir a análise.",
        }
        return {**verified_dossier(output, "regra-local", ids), "mode": "local"}


    if binary := os.getenv("ELO_ON_DEVICE_BIN"):
        return generate_on_device(binary, evidence, ids)
    if not configured():
        raise WorkflowError("Configure o modelo local ou OPENAI_API_KEY e ELO_MODEL para usar IA real.", 503)
    schema = {
        "type": "object", "additionalProperties": False, "required": ["claims", "limitations", "suggestion"],
        "properties": {
            "claims": {"type": "array", "items": {
                "type": "object", "additionalProperties": False, "required": ["text", "source_ids"],
                "properties": {"text": {"type": "string"}, "source_ids": {"type": "array", "items": {"type": "string", "enum": ids}}}}},
            "limitations": {"type": "string"}, "suggestion": {"type": "string"},
        },
    }

    request = Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps({
            "model": os.environ["ELO_MODEL"], "store": False, "instructions": INSTRUCTIONS,
            "input": json.dumps(evidence, ensure_ascii=False), "max_output_tokens": 1800,
            "text": {"format": {"type": "json_schema", "name": "dossier", "strict": True, "schema": schema}},
        }).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + os.environ["OPENAI_API_KEY"]},
    )
    try:
        with urlopen(request, timeout=30) as response:
            result = json.load(response)
        output = next(part["text"] for item in result["output"] if item["type"] == "message"
                      for part in item["content"] if part["type"] == "output_text")
        return verified_dossier(json.loads(output), result["model"], ids)
    except (URLError, TimeoutError, ValueError, KeyError, TypeError, AttributeError, StopIteration) as error:
        raise WorkflowError("A síntese por IA não foi concluída. Confira a configuração e tente novamente.", 502) from error
