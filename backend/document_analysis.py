"""Bounded local TXT processing. Extracted text is data, never an instruction."""
import hashlib
import re
from copy import deepcopy
from datetime import datetime, timezone
from domain import WorkflowError, required, require, serialize

MAX_TEXT_BYTES = 32768
VERSION = 'elo-text-review-v1'


def revision(entry):
    return hashlib.sha256(serialize({k: v for k, v in entry.items() if k != 'revision'}).encode()).hexdigest()


def extract(state, metadata, content):
    require(metadata['media_type'] == 'text/plain', 'Esta análise local aceita somente TXT UTF-8; PDF e imagens continuam como anexos.')
    require(len(content) <= MAX_TEXT_BYTES, 'A análise aceita TXT de até 32 KiB, sem truncar o documento.')
    require(hashlib.sha256(content).hexdigest() == metadata['sha256'], 'O arquivo não corresponde à fonte preservada.')
    try:
        text = content.decode('utf-8-sig')
    except UnicodeDecodeError as error:
        raise WorkflowError('O documento precisa usar texto UTF-8 válido.') from error
    require(not any(ord(char) < 32 and char not in '\t\n\r' for char in text),
            'O documento contém caracteres binários de controle.')
    require(bool(text.strip()), 'O documento não contém texto para analisar.')
    known = {row['id'] for table in state['dataset'].values() for row in table}
    mentions = sorted(set(re.findall(r'\b(?:CTR|FOR|EMP)-[A-Za-z0-9_-]+', text)))
    # Bound stored references independently of document length.
    require(len(mentions) <= 100, 'O documento excede 100 identificadores; divida o arquivo.')
    return {'attachment_id': metadata['id'], 'case_id': metadata['case_id'], 'sha256': metadata['sha256'],
            'text': text, 'record_ids': [identifier for identifier in mentions if identifier in known],
            'unknown_ids': [identifier for identifier in mentions if identifier not in known],
            'processor': VERSION, 'status': 'pending',
            'limitations': 'Extração literal e reconhecimento de IDs, sem IA, OCR ou inferência de vínculo. Referências citadas não comprovam fatos; revise o conteúdo e a pertinência ao caso.'}


def record(state, data):
    actor = required(data, 'actor', 80)
    result = data['analysis']  # Only trusted server command may supply this structure.
    entries = state.setdefault('document_analyses', [])
    require(len(entries) < 200, 'Limite local de 200 análises de documentos atingido.')
    require(not any(row['attachment_id'] == result['attachment_id'] for row in entries), 'Este arquivo já foi analisado; consulte a análise preservada.')
    source = next((row for row in state['attachments'] if row['id'] == result['attachment_id']), None)
    require(source is not None and source['sha256'] == result['sha256'] and source['case_id'] == result['case_id'], 'Fonte alterada ou indisponível.')
    entry = {**deepcopy(result), 'id': f'DOC-{len(entries)+1:03}', 'actor': actor,
             'created_at': datetime.now(timezone.utc).isoformat(timespec='milliseconds'), 'review': None}
    entry['revision'] = revision(entry)
    entries.append(entry)
    return 'Texto do documento analisado localmente', actor, {'analysis_id': entry['id'], 'attachment_id': source['id'], 'case_id': source['case_id'], 'sha256': source['sha256'], 'processor': VERSION}


def review(state, data):
    actor, reason = required(data, 'actor', 80), required(data, 'reason')
    entry = next((row for row in state.get('document_analyses', []) if row['id'] == data.get('analysis_id')), None)
    require(entry is not None, 'Análise não encontrada.')
    require(required(data, 'revision', 64) == entry['revision'], 'A análise mudou. Atualize e revise novamente.')
    require(entry['status'] == 'pending', 'Esta análise já foi revisada.')
    outcome = data.get('outcome')
    require(outcome in ('accepted', 'rejected'), 'Escolha aceitar ou rejeitar o texto como fonte.')
    require(data.get('confirmed') is True, 'Confirme a revisão humana do texto e sua pertinência ao caso.')
    entry['status'] = outcome
    entry['review'] = {'actor': actor, 'reason': reason, 'at': datetime.now(timezone.utc).isoformat(timespec='milliseconds')}
    entry['revision'] = revision(entry)
    return 'Revisão humana do documento registrada', actor, {'analysis_id': entry['id'], 'case_id': entry['case_id'], 'attachment_id': entry['attachment_id'], 'outcome': outcome, 'reason': reason}


def sources(state, case_id):
    # Maximum three accepted documents, transparent partial context handled by caller.
    return [{'id': row['attachment_id'], 'source': 'Texto sintético revisado por pessoa',
             'detail': row['text'], 'revision': row['revision'], 'sha256': row['sha256']}
            for row in state.get('document_analyses', []) if row['case_id'] == case_id and row['status'] == 'accepted']
