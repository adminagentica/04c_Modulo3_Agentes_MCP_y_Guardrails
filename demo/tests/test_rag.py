import copy
import sys
from pathlib import Path
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import rag_client


class RagValidationTests(unittest.TestCase):
    def setUp(self):
        self.bundle = {'index_version': 'idx', 'citations': [{'id':1, 'code':'POL-COB-04', 'version':'v4',
                        'section':'§5', 'content':'Evidencia', 'sourceHash':'hash'}]}
        self.docs = {'documents':[{'code':'POL-COB-04','version':'v4','active':1,'access_role':'COBRANZA',
                                  'valid_from':'2020-01-01','valid_until':None,'file_hash':'hash'}],
                     'chunks':[{'id':1,'document_code':'POL-COB-04','version':'v4','section':'§5','content':'Evidencia'}]}

    def check(self, bundle=None, docs=None, fingerprint='fp'):
        def response(path):
            return {'state':'ready','sourceFingerprint':'fp','indexVersion':'idx'} if path.endswith('status') else docs or self.docs
        with patch('rag_client.request', side_effect=response), patch('rag_client.source_fingerprint', return_value=fingerprint):
            return rag_client.validate_bundle(bundle or self.bundle)

    def test_valid_citation(self):
        self.assertTrue(self.check())

    def test_changed_files(self):
        with self.assertRaises(ValueError): self.check(fingerprint='changed')

    def test_expired_or_wrong_role(self):
        for key,value in [('valid_until','2020-01-01'),('access_role','SUPERVISION'),('active',0)]:
            with self.subTest(key=key):
                docs=copy.deepcopy(self.docs); docs['documents'][0][key]=value
                with self.assertRaises(ValueError): self.check(docs=docs)

    def test_forged_citation_or_index(self):
        for key,value in [('sourceHash','forged'),('content','texto inventado'),('section','otra'),('version','v1')]:
            with self.subTest(key=key):
                bundle=copy.deepcopy(self.bundle);bundle['citations'][0][key]=value
                with self.assertRaises(ValueError): self.check(bundle=bundle)
        bundle=copy.deepcopy(self.bundle);bundle['index_version']='new'
        with self.assertRaises(ValueError): self.check(bundle=bundle)

    def test_insufficient_evidence_does_not_fall_back(self):
        with patch('rag_client.request', side_effect=[{'state':'ready'}, {'answer':'No sé','insufficientEvidence':True}]) as http:
            with self.assertRaises(ValueError): rag_client.retrieve_rag()
            self.assertEqual(http.call_count,2)
