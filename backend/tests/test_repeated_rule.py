import json
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dossier
import laboratory
import rule_config
from domain import Store, WorkflowError, match_repeated_cases

RULE = 'repeated-contract-profile'

class RepeatedRuleTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.store = Store(Path(self.folder.name) / 'test.sqlite3')

    def test_manual_ground_truth_and_no_contact_requirement(self):
        result = laboratory.run_laboratory(rule_id=RULE)
        self.assertEqual(result['counts'], dict(total=6, expected_positive=2, predicted_positive=2, tp=2, fp=0, fn=0, tn=4))
        self.assertTrue(result['rule']['experimental'])

    def test_incremental_import_rescans_old_contract_without_duplicate_signal(self):
        self.store.apply('detect', {'rule_id': RULE})
        first = self.store.read()['dataset']['contracts'][0]
        second = {**first, 'id': 'CTR-REPEAT'}
        self.store.apply('import', {'actor':'Teste','synthetic':True,'dataset':{'employees':[], 'suppliers':[], 'contracts':[second]}})
        state = self.store.apply('detect', {'rule_id':RULE})
        self.assertEqual({c['records']['contract']['id'] for c in state['cases']}, {first['id'],second['id']})
        saved = deepcopy(state['cases'])
        third = {**first, 'id':'CTR-THIRD'}
        self.store.apply('import', {'actor':'Teste','synthetic':True,'dataset':{'employees':[], 'suppliers':[], 'contracts':[third]}})
        state = self.store.apply('detect', {'rule_id':RULE})
        self.assertEqual(len(state['cases']),3)
        self.assertEqual(state['cases'][:2],saved)
        self.assertTrue(state['audit_valid'])
        with self.assertRaises(WorkflowError): self.store.apply('detect', {'rule_id':RULE})
        self.assertEqual(Store(self.store.path).read()['cases'],state['cases'])

    def test_sources_and_local_dossier_are_not_contact_match_claims(self):
        fixture=laboratory.load_fixture(RULE)
        case=match_repeated_cases(fixture['dataset'])[0]
        answer=dossier.generate(case['evidence'],'local',RULE)
        self.assertIn('não se conclui duplicidade financeira',answer['limitations'])
        self.assertNotIn('mesmo código cadastral',answer['text'])
        self.assertEqual(set(answer['source_ids']), {r['id'] for r in case['evidence']})
        self.assertIn('related_contract',case['records'])

    def test_filter_and_disabled_rule(self):
        fixture=laboratory.load_fixture(RULE)
        config=rule_config.defaults(RULE)
        config['enabled']=False
        self.assertEqual(rule_config.match(fixture['dataset'],RULE,config),[])
        config['enabled']=True
        config['contract_title_contains']='mensal'
        self.assertEqual(rule_config.match(fixture['dataset'],RULE,config),[])

    def test_peer_selection_is_order_independent(self):
        data=laboratory.load_fixture(RULE)['dataset']
        expected=match_repeated_cases(data)
        data['contracts'].reverse()
        self.assertEqual(sorted(expected,key=lambda r:r['id']),sorted(match_repeated_cases(data),key=lambda r:r['id']))
