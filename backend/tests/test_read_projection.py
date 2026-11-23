"""Projection must not retain a SQLite reader lock or share persisted mutations."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import domain
from access_audit import AccessAudit


class ReadProjectionTests(unittest.TestCase):
    def test_projection_releases_reader_and_preserves_snapshot_isolation(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = domain.Store(Path(temporary) / 'read.sqlite3')
            store.apply('detect', {'actor': 'Synthetic'})
            ledger = AccessAudit(store.path)
            project = domain.presentation
            def project_after_commit(snapshot, case_id=None, **kwargs):
                # Separate writer must be able to commit while presentation runs.
                ledger.append(actor='test', mode='local-service', event='read', target='/api/state', outcome='success', ip='127.0.0.1')
                return project(snapshot, case_id, **kwargs)
            with patch('domain.presentation', side_effect=project_after_commit):
                state = store.read()
            self.assertTrue(state['audit_valid'])
            state['dataset']['contracts'][0]['title'] = 'caller mutation'
            self.assertNotEqual(store.read()['dataset']['contracts'][0]['title'], 'caller mutation')

    def test_default_presentation_keeps_input_unchanged_and_pending_counts(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = domain.Store(Path(temporary) / 'read.sqlite3')
            store.apply('detect', {'actor': 'Synthetic'})
            snapshot = store.export_state()
            before = domain.serialize(snapshot)
            result = domain.presentation(snapshot)
            self.assertEqual(domain.serialize(snapshot), before)
            for rule in result['rules']:
                processed = snapshot['detection']['processed_by_rule'].get(rule['id'], [])
                expected = sum(row['id'] not in processed for row in snapshot['dataset']['contracts'])
                self.assertEqual(rule['pending_count'], expected)
