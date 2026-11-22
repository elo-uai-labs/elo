"""Summarize synthetic evidence without granting decision authority."""

import json
import os
import subprocess
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

from domain import WorkflowError

PROMPT_VERSION = "elo-dossier-v2"
INSTRUCTIONS = (
    "Redija uma síntese curta de evidências sintéticas de um possível conflito de interesses. "
    "Use apenas as evidências recebidas e apenas IDs declarados. Cite os IDs junto às afirmações. "
    "Explique a coincidência e sua limitação, e sugira somente uma verificação humana. "
    "Nunca atribua culpa, confirme uma irregularidade, proponha penalidade ou decida o caso."
)


def configured():
    return bool(os.getenv("ELO_ON_DEVICE_BIN") or (os.getenv("OPENAI_API_KEY") and os.getenv("ELO_MODEL")))


def verified_dossier(output, model, ids):
    references = output["source_ids"]
    text = output["text"].strip()
    if not 0 < len(text) <= 1800 or not isinstance(references, list) or not references:
        raise ValueError("Invalid dossier shape")
    if any(not isinstance(ref, str) or ref not in ids or ref not in text for ref in references):
        raise ValueError("Invalid source IDs")
    return {"text": text, "source_ids": list(dict.fromkeys(references)), "mode": "real", "model": model, "prompt_version": PROMPT_VERSION}


def generate_on_device(binary, evidence, ids):
    citation_contract = (
        " Os únicos IDs de fontes permitidos são: " + ", ".join(ids) + ". "
        "Cada identificador listado em source_ids deve aparecer literalmente no texto, junto à afirmação correspondente. "
        "Não substitua identificadores pelos nomes dos registros."
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
                    "Gere uma nova síntese curta com os IDs literais junto às afirmações e declare somente "
                    "fontes existentes que estejam explicitamente citadas no texto."
                )
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError, AttributeError) as error:
        raise WorkflowError("A síntese por IA no dispositivo não foi concluída. Confira o modelo local e tente novamente.", 502) from error


def generate(evidence, mode):
    ids = [item["id"] for item in evidence]
    if mode == "local":
        contract, supplier, employee = ids
        return {
            "mode": "local", "model": "regra-local", "prompt_version": PROMPT_VERSION, "source_ids": ids,
            "text": f"O contrato {contract} relaciona o fornecedor {supplier} ao empregado {employee} como aprovador. "
            f"Os registros {supplier} e {employee} têm o mesmo código cadastral. A coincidência isolada não comprova "
            "irregularidade. Sugestão: verificar a origem e a validade do vínculo antes de concluir a análise.",
        }

    if binary := os.getenv("ELO_ON_DEVICE_BIN"):
        return generate_on_device(binary, evidence, ids)
    if not configured():
        raise WorkflowError("Configure o modelo local ou OPENAI_API_KEY e ELO_MODEL para usar IA real.", 503)
    schema = {
        "type": "object", "additionalProperties": False, "required": ["text", "source_ids"],
        "properties": {"text": {"type": "string"}, "source_ids": {"type": "array", "items": {"type": "string", "enum": ids}}},
    }
    request = Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps({
            "model": os.environ["ELO_MODEL"], "store": False, "instructions": INSTRUCTIONS,
            "input": json.dumps(evidence, ensure_ascii=False), "max_output_tokens": 1200,
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
