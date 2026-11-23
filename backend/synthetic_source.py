"""Explicit synthetic loopback source adapter. No corporate endpoint or default job."""
import argparse
import json
import os
import re
import socket
import sqlite3
from http.client import HTTPException
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from domain import Store, WorkflowError
from monitoring import MAX_FILE_BYTES, batch_identity, source_slug

CONTRACT = 'elo-synthetic-source-v1'
TABLES = ('employees', 'suppliers', 'contracts')
MAX_PAGES = 10
PAGE_KEYS = {'contract', 'synthetic', 'snapshot_id', 'page', 'total_pages', 'total_counts', 'dataset'}


class SourceError(ValueError):
    """Safe fixed message, never remote body, credentials or full URL."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def validate_endpoint(endpoint):
    try:
        parts = urlsplit(endpoint)
        if (parts.scheme != 'http' or parts.hostname != '127.0.0.1' or parts.netloc != f'127.0.0.1:{parts.port}'
                or not 1 <= parts.port <= 65535 or parts.path != '/snapshot' or parts.query or parts.fragment):
            raise ValueError
    except (ValueError, TypeError):
        raise SourceError('Use http://127.0.0.1:PORT/snapshot, sem credenciais ou parâmetros.') from None
    return endpoint


def fetch_snapshot(endpoint, token, *, timeout=1.0, max_attempts=2, budget=15.0):
    endpoint = validate_endpoint(endpoint)
    if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9._~-]{8,256}', token):
        raise SourceError('Credencial sintética ausente ou inválida.')
    if not (0.05 <= timeout <= 5 and type(max_attempts) is int and 1 <= max_attempts <= 3 and 0.1 <= budget <= 30):
        raise SourceError('Limites de transporte inválidos.')
    opener = build_opener(ProxyHandler({}), NoRedirect())
    deadline = time.monotonic() + budget
    datasets = {name: [] for name in TABLES}
    identity = None
    attempts = 0
    total_bytes = 0
    for page_number in range(1, MAX_PAGES + 1):
        page = None
        for attempt in range(max_attempts):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise SourceError('Orçamento de tempo da coleta excedido.')
            request = Request(f'{endpoint}?page={page_number}', headers={'Authorization': 'Bearer ' + token, 'Accept': 'application/json'})
            attempts += 1
            try:
                with opener.open(request, timeout=min(timeout, remaining)) as response:
                    if response.status != 200 or response.headers.get_content_type() != 'application/json':
                        raise SourceError('Resposta não corresponde ao contrato JSON.')
                    chunks, page_bytes = [], 0
                    while True:
                        if time.monotonic() >= deadline:
                            raise SourceError('Orçamento de tempo da coleta excedido.')
                        chunk = response.read1(min(65536, MAX_FILE_BYTES + 1 - page_bytes))
                        if not chunk:
                            break
                        chunks.append(chunk)
                        page_bytes += len(chunk)
                        if page_bytes > MAX_FILE_BYTES:
                            raise SourceError('Página excede limite de bytes.')
                    content = b''.join(chunks)
                if len(content) > MAX_FILE_BYTES:
                    raise SourceError('Página excede limite de bytes.')
                total_bytes += len(content)
                if total_bytes > MAX_FILE_BYTES:
                    raise SourceError('Coleta excede limite de bytes.')
                page = json.loads(content.decode('utf-8'))
                break
            except HTTPError as error:
                status = error.code
                error.close()
                if status != 503 or attempt + 1 == max_attempts:
                    raise SourceError(f'Fonte respondeu HTTP {status}; lote não importado.') from None
            except (URLError, TimeoutError, socket.timeout, HTTPException):
                if attempt + 1 == max_attempts:
                    raise SourceError('Transporte indisponível; lote não importado.') from None
            except (ValueError, UnicodeError) as error:
                if isinstance(error, SourceError):
                    raise
                raise SourceError('JSON inválido; lote não importado.') from None
            time.sleep(min(.05 * (attempt + 1), max(0, deadline - time.monotonic())))
        if time.monotonic() > deadline:
            raise SourceError('Orçamento de tempo da coleta excedido.')
        if not isinstance(page, dict) or set(page) != PAGE_KEYS or page['contract'] != CONTRACT or page['synthetic'] is not True:
            raise SourceError('Versão ou campos do contrato não suportados.')
        snapshot_id, total_pages, counts = page['snapshot_id'], page['total_pages'], page['total_counts']
        if not isinstance(snapshot_id, str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,47}', snapshot_id):
            raise SourceError('Identificador do snapshot inválido.')
        if type(page['page']) is not int or page['page'] != page_number or type(total_pages) is not int or not page_number <= total_pages <= MAX_PAGES:
            raise SourceError('Paginação inválida.')
        if not isinstance(counts, dict) or set(counts) != set(TABLES) or any(type(v) is not int or not 0 <= v <= 500 for v in counts.values()):
            raise SourceError('Contagens esperadas inválidas.')
        page_identity = (snapshot_id, total_pages, counts)
        if identity is not None and identity != page_identity:
            raise SourceError('Snapshot mudou durante a coleta; lote não importado.')
        identity = page_identity
        dataset = page['dataset']
        if not isinstance(dataset, dict) or set(dataset) != set(TABLES) or any(not isinstance(dataset[name], list) for name in TABLES):
            raise SourceError('Tabelas do contrato inválidas.')
        for name in TABLES:
            datasets[name].extend(dataset[name])
            if len(datasets[name]) > counts[name]:
                raise SourceError('Quantidade recebida excede reconciliação.')
        if page_number == total_pages:
            break
    if any(len(datasets[name]) != identity[2][name] for name in TABLES):
        raise SourceError('Reconciliação de contagens falhou.')
    for rows in datasets.values():
        if any(not isinstance(row, dict) or not isinstance(row.get('id'), str) for row in rows):
            raise SourceError('Registro sem identificador válido.')
        if len({row['id'] for row in rows}) != len(rows):
            raise SourceError('Identificador duplicado entre páginas.')
        rows.sort(key=lambda row: row['id'])  # Content identity independent of page ordering.
    return {'payload': {'synthetic': True, 'dataset': datasets}, 'snapshot_id': identity[0],
            'pages': identity[1], 'counts': identity[2], 'attempts': attempts}


def ingest(store, endpoint, token, source_id, **limits):
    source_id = source_slug(source_id)
    collected = fetch_snapshot(endpoint, token, **limits)
    data = {'source_id': source_id, 'source_name': 'http-' + collected['snapshot_id'] + '.json', 'payload': collected['payload']}
    _, _, content_hash, _ = batch_identity(data)
    def prior(snapshot):
        if not snapshot.get('audit_valid'):
            raise SourceError('Integridade do destino inválida.')
        return next((batch for batch in snapshot.get('integration_batches', [])
                     if batch['source_id'] == source_id and batch['content_sha256'] == content_hash), None)
    batch = prior(store.read())
    status = 'duplicate' if batch else 'processed'
    if batch is None:
        try:
            state = store.apply('integration/import', data, authorize=lambda _: {'mode': 'local-service', 'service_id': source_id})
            batch = prior(state)
        except WorkflowError:
            batch = prior(store.read())
            if batch is None:
                raise SourceError('Validação ou gravação do lote recusada; consulte o estado local.') from None
            status = 'duplicate'
    received = {name: [row['id'] for row in collected['payload']['dataset'][name]] for name in TABLES}
    if batch['record_ids'] != received:
        raise SourceError('Reconciliação dos IDs importados falhou.')
    return {'status': status, 'contract': CONTRACT, 'source_id': source_id, 'snapshot_id': collected['snapshot_id'],
            'batch_id': batch['id'], 'content_sha256': content_hash, 'pages': collected['pages'],
            'attempts': collected['attempts'], 'counts': collected['counts'], 'record_ids': received,
            'reconciled': True, 'scope': 'synthetic-loopback-only'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--endpoint', required=True)
    parser.add_argument('--source-id', required=True)
    parser.add_argument('--db', type=Path, required=True)
    parser.add_argument('--synthetic', action='store_true', required=True)
    args = parser.parse_args()
    project_data = Path(__file__).resolve().parents[1] / 'data'
    if args.db.resolve().is_relative_to(project_data.resolve()):
        parser.error('Escolha um banco de ensaio fora de data/.')
    try:
        result = ingest(Store(args.db), args.endpoint, os.environ.get('ELO_SYNTHETIC_SOURCE_TOKEN', ''), args.source_id)
        print(json.dumps(result, ensure_ascii=False))
    except (SourceError, WorkflowError, OSError, sqlite3.Error):
        parser.exit(2, 'Coleta sintética recusada; nenhum sucesso deve ser presumido. Confira contrato, credencial e destino.\n')


if __name__ == '__main__':
    main()
