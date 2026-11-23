"""Bounded local document processing; extracted content is data, never instructions."""
import hashlib
import re
import csv
import io
import json
import subprocess
import sys
from pathlib import Path
from copy import deepcopy
from datetime import datetime, timezone
from domain import WorkflowError, required, require, serialize

MAX_TEXT_BYTES = 32768
VERSION = 'elo-document-review-v2'
XLSX_TYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


def revision(entry):
    return hashlib.sha256(serialize({k: v for k, v in entry.items() if k != 'revision'}).encode()).hexdigest()


def _utf8(content):
    try:
        text = content.decode('utf-8-sig')
    except UnicodeDecodeError as error:
        raise WorkflowError('O documento precisa usar texto UTF-8 válido.') from error
    require(not any(ord(char) < 32 and char not in '\t\n\r' for char in text),
            'O documento contém caracteres binários de controle.')
    return text


def _pdf(content):
    # The parser is isolated from the API process, with CPU and wall-clock bounds (address-space cap on Linux).
    try:
        result = subprocess.run([sys.executable, '-I', str(Path(__file__).with_name('pdf_text.py'))],
            input=content, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise WorkflowError('Extração PDF inconclusiva: limite de processamento ou leitor indisponível.') from error
    require(result.returncode == 0, 'Extração PDF inconclusiva: arquivo inválido, protegido, acima dos limites ou leitor não instalado. Instale requirements-documents.txt no ambiente Python.')
    try:
        return json.loads(result.stdout)
    except (ValueError, UnicodeDecodeError) as error:
        raise WorkflowError('Extração PDF inconclusiva.') from error


def _column(number):
    result = ''
    while number:
        number, remainder = divmod(number - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _sheet_segments(content, media):
    segments = []
    if media == XLSX_TYPE:
        from tabular_import import read_xlsx, ImportFormatError
        try:
            names, _, _ = read_xlsx(content)
            require(len(names) <= 10, 'Limite de 10 abas por evidência.')
            tables = [(name, read_xlsx(content, name)[2]) for name in names]
        except ImportFormatError as error:
            raise WorkflowError(f'Planilha inconclusiva: {error}') from error
    else:
        require(len(content) <= MAX_TEXT_BYTES, 'CSV de evidência aceita até 32 KiB.')
        text = _utf8(content)
        try:
            delimiter = ';' if text.splitlines()[0].count(';') > text.splitlines()[0].count(',') else ','
            rows = list(csv.reader(io.StringIO(text, newline=''), delimiter=delimiter, strict=True))
        except (csv.Error, IndexError) as error:
            raise WorkflowError('CSV inconclusivo: estrutura inválida ou vazia.') from error
        require(len(rows) <= 501, 'Limite de 501 linhas por evidência CSV.')
        tables = [('CSV', list(enumerate(rows, 1)))]
    for name, rows in tables:
        for row_number, cells in rows:
            require(len(cells) <= 32, 'Limite de 32 colunas por evidência.')
            for index, value in enumerate(cells, 1):
                if str(value).strip():
                    coordinate = f'{_column(index)}{row_number}'
                    segments.append({'sheet': name, 'cell': coordinate,
                        'location': f'{name}!{coordinate}', 'text': str(value)})
                    require(len(segments) <= 2000, 'Limite de 2.000 células preenchidas por evidência.')
    return segments


def extract(state, metadata, content):
    media = metadata['media_type']
    require(media in ('text/plain', 'text/csv', 'application/pdf', XLSX_TYPE),
            'Análise disponível para TXT, CSV, XLSX e PDF digital. Imagens precisam de OCR, ainda não implementado.')
    require(len(content) <= 1024 * 1024, 'A análise aceita arquivos de até 1 MiB.')
    require(hashlib.sha256(content).hexdigest() == metadata['sha256'], 'O arquivo não corresponde à fonte preservada.')
    missing = []
    if media == 'text/plain':
        require(len(content) <= MAX_TEXT_BYTES, 'A análise aceita TXT de até 32 KiB, sem truncar o documento.')
        text = _utf8(content)
        require(bool(text.strip()), 'O documento não contém texto para analisar.')
        segments = [{'location': f'Linha {number}', 'line': number, 'text': line}
                    for number, line in enumerate(text.splitlines(), 1) if line.strip()]
    elif media == 'application/pdf':
        result = _pdf(content)
        segments, missing = result['segments'], result['missing_pages']
        text = '\n\n'.join(f"[{row['location']}]\n{row['text']}" for row in segments)
    else:
        segments = _sheet_segments(content, media)
        text = '\n'.join(f"[{row['location']}] {row['text']}" for row in segments)
    require(len(text.encode('utf-8')) <= MAX_TEXT_BYTES, 'O texto extraído excede 32 KiB; divida o documento. Nenhum trecho foi aceito.')
    require(len(segments) <= 2000, 'O documento excede 2.000 trechos; divida o arquivo.')
    _utf8(text.encode('utf-8'))
    known = {row['id'] for table in state['dataset'].values() for row in table}
    mentions = sorted(set(re.findall(r'\b(?:CTR|FOR|EMP)-[A-Za-z0-9_-]+', text)))
    require(len(mentions) <= 100, 'O documento excede 100 identificadores; divida o arquivo.')
    complete = bool(text.strip()) and not missing
    limitations = ('Extração literal sem IA, OCR ou inferência de vínculo. PDF pode perder ordem visual; planilhas mostram valores literais, sem executar fórmulas. '
                  'Referências não comprovam fatos; confira cada página/célula no original antes de aceitar.')
    if not complete:
        limitations += ' Extração inconclusiva: páginas sem texto digital ' + ', '.join(map(str, missing)) + '. Revisão de aceitação bloqueada; não há OCR.'
    return {'attachment_id': metadata['id'], 'case_id': metadata['case_id'], 'sha256': metadata['sha256'],
            'text': text, 'segments': segments, 'extraction_status': 'complete' if complete else 'inconclusive',
            'missing_pages': missing, 'record_ids': [identifier for identifier in mentions if identifier in known],
            'unknown_ids': [identifier for identifier in mentions if identifier not in known],
            'processor': VERSION, 'status': 'pending', 'limitations': limitations}


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
    require(outcome != 'accepted' or (entry.get('extraction_status', 'complete') == 'complete' and bool(entry['text'].strip())),
            'Extração inconclusiva não pode ser aceita como fonte. Consulte o original ou rejeite a análise.')
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
