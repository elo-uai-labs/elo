import copy
import sqlite3
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from access_audit import AccessAudit, verify_database, verify_package
from domain import Store


class AccessAuditTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / 'test.sqlite3'
        self.store = Store(self.path)
        self.ledger = AccessAudit(self.path)
        self.event = dict(actor='analyst-1', mode='local-auth', event='read', target='/api/state', outcome='success', ip='127.0.0.1')

    def test_events_independent_snapshot_restart_export(self):
        before = self.store.export_state(include_files=True)
        for event in ('read', 'login', 'logout', 'export', 'download', 'denial', 'write'):
            self.ledger.append(**{**self.event, 'event': event})
        self.assertEqual(self.store.export_state(include_files=True), before)
        package = AccessAudit(self.path).export()
        self.assertEqual(package['manifest']['count'], 7)
        self.assertTrue(verify_package(package))
        with closing(sqlite3.connect(self.path)) as db:
            self.assertTrue(verify_database(db))
            for command in ('UPDATE access_audit SET hash="x"', 'DELETE FROM access_audit'):
                with self.assertRaises(sqlite3.IntegrityError):
                    db.execute(command)

    def test_concurrent_append_serializes_chain(self):
        with ThreadPoolExecutor(max_workers=5) as pool:
            results = list(pool.map(lambda _: self.ledger.append(**self.event), range(20)))
        self.assertEqual(sorted(row['seq'] for row in results), list(range(1, 21)))
        self.assertTrue(verify_package(self.ledger.export()))

    def test_append_lock_releases_after_failure_and_multiple_instances_coexist(self):
        with self.assertRaises(ValueError):
            self.ledger.append(**{**self.event, 'event': 'invalid'})
        other = AccessAudit(self.path)
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit((self.ledger if i % 2 else other).append, **self.event) for i in range(40)]
            results = [future.result(timeout=10) for future in futures]
        self.assertEqual(sorted(row['seq'] for row in results), list(range(1, 41)))
        self.assertTrue(verify_package(other.export()))

    def test_invalid_inputs_do_not_persist(self):
        for changes in ({'target': '/api/state?token=secret'}, {'target': '/api/state\n'}, {'actor': 'untrusted login text'},
                        {'mode': 'corporate-auth'}, {'ip': 'not-an-ip'}, {'outcome': 'unknown'}, {'event': 'password'}):
            with self.assertRaises(ValueError):
                self.ledger.append(**{**self.event, **changes})
        self.assertEqual(self.ledger.export()['events'], [])

    def test_tampered_database_blocks_export_and_append(self):
        self.ledger.append(**self.event)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('DROP TRIGGER access_audit_no_update')
            db.execute("UPDATE access_audit SET hash='tampered'")
        with self.assertRaises(ValueError):
            self.ledger.export()
        with self.assertRaises(ValueError):
            self.ledger.append(**self.event)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertFalse(verify_database(db))
            self.assertEqual(db.execute('SELECT COUNT(*) FROM access_audit').fetchone()[0], 1)

    def test_package_rejects_tampering_extra_fields_and_reordering(self):
        self.ledger.append(**self.event)
        self.ledger.append(**{**self.event, 'event': 'logout'})
        for mutation in (lambda p: p['events'][0].update(actor='other'),
                         lambda p: p['events'].reverse(), lambda p: p['events'].pop(),
                         lambda p: p['manifest'].update(count=1), lambda p: p.update(secret='hidden'),
                         lambda p: p['events'][0].update(secret='hidden')):
            package = copy.deepcopy(self.ledger.export())
            mutation(package)
            self.assertFalse(verify_package(package))

    def test_legacy_missing_table_is_readonly_compatible(self):
        legacy = self.path.with_name('legacy.sqlite3')
        Store(legacy)
        before = legacy.read_bytes()
        with closing(sqlite3.connect(legacy)) as db:
            self.assertTrue(verify_database(db))
        self.assertEqual(legacy.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
