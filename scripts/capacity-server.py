"""Test-only launcher: classify ledger failures without recording data or secrets."""
import json
from pathlib import Path
import runpy
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from access_audit import AccessAudit

original_append = AccessAudit.append


def observed_append(self, **kwargs):
    try:
        return original_append(self, **kwargs)
    except (sqlite3.Error, ValueError, TypeError, KeyError, OverflowError) as error:
        print('CAPACITY_LEDGER_FAILURE ' + json.dumps({'type': type(error).__name__,
              'sqlite_errorcode': getattr(error, 'sqlite_errorcode', None),
              'sqlite_errorname': getattr(error, 'sqlite_errorname', None)}), file=sys.stderr, flush=True)
        raise


AccessAudit.append = observed_append
runpy.run_path(str(ROOT / 'backend/server.py'), run_name='__main__')
