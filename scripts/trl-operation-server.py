"""Test-only authenticated Elo process; configurable real session expiry."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from access import AccessService
from domain import Store
from server import EloServer

parser = argparse.ArgumentParser()
parser.add_argument('--db', type=Path, required=True)
parser.add_argument('--users', type=Path, required=True)
parser.add_argument('--port', type=int, required=True)
parser.add_argument('--ttl', type=float, default=3600)
args = parser.parse_args()
with EloServer(('127.0.0.1', args.port), Store(args.db),
               access_service=AccessService(args.users, session_ttl=args.ttl)) as server:
    server.serve_forever()
