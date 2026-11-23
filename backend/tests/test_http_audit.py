import base64
import json
import io
import socket
import sqlite3
import sys
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from domain import Store
from server import EloServer
from access import AccessService, provision
from access_audit import verify_package


class HttpAuditTest(unittest.TestCase):
    def setUp(self):
        directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup)
        self.root=Path(directory.name);self.store=Store(self.root/'test.db')
        self.server=EloServer(('127.0.0.1',0), self.store, access_service=None)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.addCleanup(self.shutdown)

    def shutdown(self):
        self.server.shutdown();self.server.server_close();self.thread.join()

    def request(self, method='GET',path='/api/state',data=None,headers=None):
        conn=HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
        try:
            conn.request(method,path,json.dumps(data) if data is not None else None,{'Content-Type':'application/json',**(headers or {})})
            response=conn.getresponse();return response.status,dict(response.getheaders()),response.read()
        finally:conn.close()

    def test_malformed_request_does_not_log_raw_credentials(self):
        output = io.StringIO()
        with patch('sys.stderr', output):
            with socket.create_connection(self.server.server_address, timeout=5) as client:
                client.sendall(b'GET /api/state?token=secret-test EXTRA HTTP/1.1\r\n\r\n')
                self.assertIn(b'400', client.recv(4096))
        self.assertNotIn('secret-test', output.getvalue())
        self.assertIn('HTTP request rejected', output.getvalue())

    def test_reads_export_download_record_origin_without_business_mutation(self):
        before=self.store.export_state()
        self.assertEqual(self.request(headers={'X-Forwarded-For':'203.0.113.7'})[0],200)
        self.assertEqual(self.store.export_state(),before)
        self.request('POST','/api/detect',{})
        self.request('POST','/api/evidence/upload',{'actor':'Persona','case_id':'ELO-1042','synthetic':True,'name':'ata.txt','media_type':'text/plain','description':'Sintético','content_base64':base64.b64encode(b'ATA').decode()})
        self.request(path='/api/evidence/EVD-0001')
        self.request(path='/api/audit/export')
        status,_,body=self.request(path='/api/access-audit/export')
        self.assertEqual(status,200)
        package=json.loads(body);self.assertTrue(verify_package(package))
        events=package['events']
        self.assertTrue(any(e['event']=='download' and e['target']=='/api/evidence/EVD-0001' for e in events))
        self.assertTrue(any(e['event']=='export' and e['target']=='/api/audit/export' for e in events))
        self.assertTrue(all(e['ip']=='127.0.0.1' for e in events))
        self.assertNotIn('ATA',json.dumps(events))
        self.assertNotIn('Persona',json.dumps(events))

    def test_auth_denial_login_canonical_logout_and_audit_failure(self):
        file=self.root/'users.json';password='temporary-secret-12345'
        provision(file,'auditor','Auditor',['auditor'],password)
        self.server.access=AccessService(file)
        self.assertEqual(self.request()[0],401)
        self.assertEqual(self.request('POST','/api/login',{'username':'ATTACKER-INJECT','password':'unlogged-secret'})[0],401)
        status,headers,_=self.request('POST','/api/login',{'username':'auditor','password':password})
        self.assertEqual(status,200);cookie=headers['Set-Cookie'].split(';')[0]
        self.assertEqual(self.request(headers={'Cookie':cookie})[0],200)
        self.assertEqual(self.request('POST','/api/logout',{},headers={'Cookie':cookie})[0],200)
        package=self.server.access_audit.export()
        self.assertTrue(verify_package(package))
        self.assertTrue(any(e['event']=='login' and e['actor']=='auditor' for e in package['events']))
        self.assertTrue(any(e['event']=='logout' and e['actor']=='auditor' for e in package['events']))
        self.assertNotIn('unlogged-secret',json.dumps(package));self.assertNotIn('ATTACKER-INJECT',json.dumps(package))
        with patch.object(self.server.access_audit,'append',side_effect=sqlite3.OperationalError('offline')):
            status,_,body=self.request()
            self.assertEqual(status,503)
            self.assertNotIn(b'dataset',body)
