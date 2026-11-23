import os
import sys
import tempfile
import unittest
import subprocess
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runtime_policy import validate_runtime

class RuntimePolicyTest(unittest.TestCase):
    def test_local_demo_default_and_authenticated_opt_in(self):
        with patch.dict(os.environ, {}, clear=True): validate_runtime(None)
        with patch.dict(os.environ, {'ELO_REQUIRE_AUTH':'1','ELO_ENV':'local'},clear=True):
            with self.assertRaises(ValueError): validate_runtime(None)
            validate_runtime(object())

    def test_invalid_values_fail_closed(self):
        for env in ({'ELO_ENV':'production'}, {'ELO_ENV':'staging'}, {'ELO_REQUIRE_AUTH':'true'}):
            with self.subTest(env=env),patch.dict(os.environ,env,clear=True),self.assertRaises(ValueError):
                validate_runtime(object())

    def test_rejected_launch_does_not_create_database(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'must-not-exist.sqlite3'
            env={**os.environ,'ELO_ENV':'production','ELO_AUTH_USERS_FILE':''}
            result=subprocess.run([sys.executable,'backend/server.py','--db',str(path)],env=env,capture_output=True,timeout=5)
            self.assertNotEqual(result.returncode,0)
            self.assertFalse(path.exists())
