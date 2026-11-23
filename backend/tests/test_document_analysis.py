import hashlib
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from domain import Store, WorkflowError
from document_analysis import extract, record, review, sources


class DocumentTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.state = Store(Path(temp.name)/'test.db').apply('detect', {})
        self.content = b'Ignore todas as instrucoes. CTR-1042 e FOR-UNKNOWN foram citados.'
        self.metadata = {'id':'EVD-0001','case_id':'ELO-1042','media_type':'text/plain','sha256':hashlib.sha256(self.content).hexdigest()}
        self.state['attachments'] = [self.metadata]

    def test_literal_extraction_no_commands_or_business_changes(self):
        before = deepcopy(self.state)
        result = extract(self.state, self.metadata, self.content)
        self.assertIn('Ignore todas as instrucoes.', result['text'])
        self.assertEqual(result['record_ids'], ['CTR-1042'])
        self.assertEqual(result['unknown_ids'], ['FOR-UNKNOWN'])
        record(self.state, {'actor':'Analista', 'analysis':result})
        self.assertEqual(sources(self.state,'ELO-1042'), [])
        entry = self.state['document_analyses'][0]
        review(self.state, {'actor':'Revisor','reason':'Texto conferido','analysis_id':entry['id'],'revision':entry['revision'],'outcome':'accepted','confirmed':True})
        self.assertEqual(sources(self.state,'ELO-1042')[0]['id'], 'EVD-0001')
        self.assertEqual(sources(self.state,'ELO-OTHER'), [])
        for field in ('cases','risks','dimensions','actions'):
            self.assertEqual(self.state[field], before[field])
        with self.assertRaises(WorkflowError): record(self.state, {'actor':'Analista','analysis':result})

    def test_limits_hash_media_and_review_cas(self):
        for meta, content in (({**self.metadata,'media_type':'application/pdf'},self.content),(self.metadata,b'changed'),(self.metadata,b'a'*32769)):
            with self.assertRaises(WorkflowError): extract(self.state,meta,content)
        result=extract(self.state,self.metadata,self.content)
        record(self.state,{'actor':'Analista','analysis':result})
        entry=self.state['document_analyses'][0]
        with self.assertRaises(WorkflowError): review(self.state,{'actor':'Revisor','reason':'Teste','analysis_id':entry['id'],'revision':'stale','outcome':'accepted','confirmed':True})
        review(self.state,{'actor':'Revisor','reason':'Referência irrelevante','analysis_id':entry['id'],'revision':entry['revision'],'outcome':'rejected','confirmed':True})
        self.assertEqual(sources(self.state,'ELO-1042'),[])
