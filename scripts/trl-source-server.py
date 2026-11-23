"""Disposable standalone synthetic source service for integration acceptance."""
import argparse
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from threading import Lock
import time
from urllib.parse import parse_qs, urlsplit

DATA = {
    'employees': [{'id': 'EMP-HTTP', 'name': 'Pessoa sintética HTTP', 'role': 'Aprovador', 'contact_code': 'SYN-HTTP'}],
    'suppliers': [{'id': 'FOR-HTTP', 'name': 'Fornecedor sintético HTTP', 'contact_code': 'SYN-HTTP'}],
    'contracts': [{'id': 'CTR-HTTP', 'title': 'Contrato sintético HTTP', 'supplier_id': 'FOR-HTTP', 'approver_id': 'EMP-HTTP'}],
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenario', default='success', choices=['success', 'unauthorized', 'retry503', 'timeout', 'always503',
        'schema', 'drift', 'duplicate', 'missing-reference', 'counts', 'oversized', 'redirect'])
    args = parser.parse_args()
    token = os.environ['ELO_SYNTHETIC_SOURCE_TOKEN']
    attempts, lock = {}, Lock()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_GET(self):
            if urlsplit(self.path).path != '/snapshot':
                self.send_error(404)
                return
            page_number = int(parse_qs(urlsplit(self.path).query).get('page', ['1'])[0])
            with lock:
                attempts[page_number] = attempts.get(page_number, 0) + 1
                attempt = attempts[page_number]
            status, body = 200, None
            if self.headers.get('Authorization') != 'Bearer ' + token or args.scenario == 'unauthorized':
                status = 401
            elif args.scenario == 'always503' or (args.scenario == 'retry503' and page_number == 2 and attempt == 1):
                status = 503
            elif args.scenario == 'redirect':
                self.send_response(302)
                self.send_header('Location', 'http://127.0.0.1:1/credential-must-not-be-forwarded')
                self.end_headers()
                return
            if args.scenario == 'timeout' and page_number == 1 and attempt == 1:
                time.sleep(.3)
            if status == 200:
                data = deepcopy(DATA)
                if args.scenario == 'missing-reference':
                    data['contracts'][0]['approver_id'] = 'EMP-NOT-PRESENT'
                dataset = {name: data[name] if (page_number == 1 and name != 'contracts') or (page_number == 2 and name == 'contracts') else [] for name in DATA}
                counts = {name: 1 for name in DATA}
                if args.scenario == 'duplicate':
                    counts['employees'] = 2
                    if page_number == 2:
                        dataset['employees'] = data['employees']
                if args.scenario == 'counts':
                    counts['contracts'] = 2
                body = {'contract': 'elo-synthetic-source-v1' if args.scenario != 'schema' else 'incompatible-v2',
                        'synthetic': True, 'snapshot_id': 'sample-v1' if not (args.scenario == 'drift' and page_number == 2) else 'sample-v2',
                        'page': page_number, 'total_pages': 2, 'total_counts': counts, 'dataset': dataset}
            encoded = json.dumps(body or {'error': 'synthetic-source-error'}).encode()
            if args.scenario == 'oversized':
                encoded = b' ' * (512 * 1024 + 1)
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(encoded)))
            self.end_headers()
            try:
                self.wfile.write(encoded)
            except (BrokenPipeError, ConnectionResetError):
                pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    print(json.dumps({'port': server.server_port, 'pid': os.getpid(), 'scope': 'synthetic-loopback-only'}), flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
