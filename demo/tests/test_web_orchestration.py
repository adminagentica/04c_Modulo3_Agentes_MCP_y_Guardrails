from pathlib import Path
import sys,tempfile,unittest,uuid,json
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from cobranza import Store
from customer_service import CustomerService
from web_orchestration import ChatOrchestrator, ask_n8n, N8nUnavailable


class WebOrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.service=CustomerService(Store(Path(self.tmp.name)/'test.sqlite'));self.service.seed()
        self.chat=ChatOrchestrator(self.service);self.ident=str(uuid.uuid4())
    def tearDown(self):self.tmp.cleanup()
    def prepare(self):return self.chat.prepare('¿Cuál es el saldo del DNI 74851236?','74851236',self.ident)
    def response(self,**overrides):
        value={'request_id':self.ident,'intro':'Consulta verificada contra las fuentes disponibles.','policy_answer':'','citation_ids':[],'state':'answered',**overrides}
        return {'model':'gpt-5.4-mini','output':[{'content':[{'type':'output_text','text':json.dumps(value)}]}],'usage':{'total_tokens':99}}
    def test_context_payload_does_not_contain_email_key_or_full_dni(self):
        result=self.prepare();payload=result['openai_payload'];self.assertTrue(result['call_openai'])
        self.assertNotIn('contacto@',payload['input']);self.assertNotIn('74851236',payload['input'])
        self.assertNotIn('api_key',json.dumps(payload));self.assertFalse(payload['store'])
    def test_balance_is_authoritative_and_execution_visible(self):
        self.prepare();r=self.chat.complete(self.ident,self.response(),200,'123')
        self.assertIn('1500.00',r['answer']);self.assertEqual(r['execution_id'],'123');self.assertEqual(r['orchestrated_by'],'n8n')
    def test_model_cannot_insert_balance_in_unrequested_policy_answer(self):
        self.prepare()
        with self.assertRaises(ValueError):self.chat.complete(self.ident,self.response(policy_answer='Tu saldo es 99.'),200,'123')
    def test_changed_balance_stops_response(self):
        self.prepare()
        with self.service.store.connect() as c:c.execute("UPDATE cases SET balance_cents=10 WHERE id='MAIL-DEMO-001'")
        with self.assertRaises(ValueError):self.chat.complete(self.ident,self.response(),200,'123')
    def test_quota_is_reported_not_replaced_by_fake_answer(self):
        self.prepare();r=self.chat.complete(self.ident,{'error':{'code':'insufficient_quota'}},429,'123')
        self.assertEqual(r['state'],'error');self.assertIn('crédito',r['answer']);self.assertNotIn('1500',r['answer'])
    def test_wrong_key_is_reported(self):
        self.prepare();r=self.chat.complete(self.ident,{'error':{'code':'invalid_api_key'}},401,'123')
        self.assertEqual(r['error_code'],'invalid_api_key');self.assertIn('n8n',r['answer'])
    def test_missing_customer_skips_openai(self):
        self.assertFalse(self.chat.prepare('saldo','12345678',self.ident)['call_openai'])
    def test_question_establishes_missing_selected_identity(self):
        self.assertTrue(self.chat.prepare('saldo DNI 40112233','',self.ident)['call_openai'])
    def test_explicit_customer_overrides_old_selected_field(self):
        self.assertTrue(self.chat.prepare('saldo DNI 40112233','74851236',self.ident)['call_openai'])
    def test_retrieval_only_for_policy_questions(self):
        with patch('web_orchestration.retrieve_passages') as rag:self.prepare();rag.assert_not_called()
    def test_greeting_skips_paid_call(self):
        self.assertFalse(self.chat.prepare('hola','',self.ident)['call_openai'])
    def test_missing_policy_skips_paid_call(self):
        with patch('web_orchestration.retrieve_passages',return_value={'index_version':'idx','citations':[]}):
            self.assertFalse(self.chat.prepare('política POL-COB-99','',self.ident)['call_openai'])
    def test_forged_source_is_rejected(self):
        citation={'id':7,'code':'POL-COB-04','version':'v4','section':'§5','content':'Texto','sourceHash':'a'*64}
        with patch('web_orchestration.retrieve_passages',return_value={'index_version':'idx','citations':[citation]}):
            self.chat.prepare('¿Qué política de contacto aplica?','',self.ident)
        with self.assertRaises(ValueError):self.chat.complete(self.ident,self.response(policy_answer='Regla [99]',citation_ids=[99]),200,'123')
    def test_n8n_failure_has_no_direct_answer_fallback(self):
        with patch('web_orchestration.urllib.request.build_opener') as opener:
            opener.return_value.open.side_effect=OSError('n8n down')
            with self.assertRaises(N8nUnavailable):ask_n8n('saldo','74851236','token-test')
