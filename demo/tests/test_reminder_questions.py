from pathlib import Path
import json,sys,tempfile,unittest,uuid
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from cobranza import Store,stamp
from customer_service import CustomerService,MAILBOX
from web_orchestration import ChatOrchestrator


class ReminderQuestionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.service=CustomerService(Store(Path(self.tmp.name)/'case.sqlite'));self.service.seed()
        self.chat=ChatOrchestrator(self.service);self.ident=str(uuid.uuid4())
        self.question='cual es el saldo de 74851236 y puedo mandarle un recordatorio de deuda?'
        self.rag={'index_version':'test-index','citations':[{'id':3,'code':'POL-COB-04','version':'v4','section':'§3 Condiciones de contacto','content':'Validar canales autorizados.','sourceHash':'a'*64}]}
    def tearDown(self):self.tmp.cleanup()
    def prepare(self):
        with patch('web_orchestration.retrieve_passages',return_value=self.rag):
            return self.chat.prepare(self.question,'74851236',self.ident)
    def response(self,policy='Revisar el canal autorizado antes del contacto [3].',state='answered'):
        value={'request_id':self.ident,'intro':'Necesito información adicional para responder.','policy_answer':policy,'citation_ids':[3] if policy else [],'state':state}
        return {'model':'mock-no-api','output':[{'content':[{'type':'output_text','text':json.dumps(value)}]}]}
    def complete(self,response=None):
        with patch('web_orchestration.validate_bundle',return_value=True):
            return self.chat.complete(self.ident,response or self.response(),200,'mock-0')
    def reserve_prior(self):
        case=self.service.store.case('demo','MAIL-DEMO-001')
        with self.service.store.connect() as c:
            c.execute('INSERT INTO outbox VALUES(?,?,?,?,?,?,?,?,?)',(self.service.store.idempotency_key(case),'demo',case['id'],'previous',case['version'],'captured',stamp(),'fixture','fixture'))
    def test_both_intents_are_detected(self):
        p=self.prepare();self.assertTrue(p['call_openai'])
        data=json.loads(p['openai_payload']['input'])
        self.assertEqual(data['route'],'account+reminder+rag');self.assertTrue(data['reminder_check']['can_prepare'])
        self.assertNotIn(MAILBOX,p['openai_payload']['input'])
    def test_original_question_answers_balance_and_reminder(self):
        self.prepare();result=self.complete()
        self.assertIn('1500.00',result['answer']);self.assertIn('permiten preparar un borrador',result['answer'])
        self.assertIn('Esta consulta no envía correos',result['answer']);self.assertFalse(result['reminder_check']['sent'])
        self.assertNotIn('Necesito información adicional',result['answer'])
        with self.service.store.connect() as c:self.assertEqual(c.execute('SELECT count(*) FROM email_inquiries').fetchone()[0],0)
    def test_zero_balance_blocks_reminder(self):
        with self.service.store.connect() as c:c.execute("UPDATE cases SET balance_cents=0 WHERE id='MAIL-DEMO-001'")
        prepared=self.prepare();self.assertFalse(prepared['call_openai']);result=prepared['response']
        self.assertFalse(result['reminder_check']['can_prepare']);self.assertIn('no existe saldo pendiente',result['answer'])
    def test_dispute_blocks_reminder(self):
        with self.service.store.connect() as c:c.execute("UPDATE cases SET disputed=1 WHERE id='MAIL-DEMO-001'")
        self.assertFalse(self.service.reminder_eligibility('74851236')['can_prepare'])
    def test_existing_reminder_blocks(self):
        self.reserve_prior();check=self.service.reminder_eligibility('74851236')
        self.assertFalse(check['can_prepare']);self.assertIn('recordatorio_ya_reservado',check['blocking_reasons'])
    def test_contact_history_rechecked_after_model(self):
        self.prepare();self.reserve_prior();result=self.complete()
        self.assertFalse(result['reminder_check']['can_prepare']);self.assertEqual(result['state'],'needs_review')
    def test_missing_rag_preserves_balance_and_explicit_limits(self):
        with patch('web_orchestration.retrieve_passages',side_effect=OSError):
            result=self.chat.prepare(self.question,'74851236',self.ident)
        self.assertFalse(result['call_openai']);self.assertIn('1500.00',result['response']['answer'])
        self.assertIn('Revisión documental pendiente',result['response']['answer']);self.assertEqual(result['response']['state'],'needs_review')
    def test_empty_documentary_evidence_does_not_authorize_send(self):
        with patch('web_orchestration.retrieve_passages',return_value={'citations':[]}):
            result=self.chat.prepare(self.question,'74851236',self.ident)
        self.assertFalse(result['call_openai']);self.assertFalse(result['response']['reminder_check']['sent'])
        self.assertEqual(result['response']['state'],'needs_review')
    def test_model_vague_intro_does_not_hide_reminder_evaluation(self):
        self.prepare();result=self.complete(self.response(policy=''))
        self.assertIn('Recordatorio:',result['answer']);self.assertNotIn('Necesito información adicional',result['answer'])
        self.assertEqual(result['state'],'needs_review')
    def test_email_change_blocks_preview(self):
        with self.service.store.connect() as c:c.execute("UPDATE cases SET recipient='otro@example.test' WHERE id='MAIL-DEMO-001'")
        check=self.service.reminder_eligibility('74851236')
        self.assertFalse(check['can_prepare']);self.assertIn('correo_no_coincide_con_registro',check['blocking_reasons'])
    def test_default_sending_engine_not_weakened(self):
        case=self.service.store.case('demo','MAIL-DEMO-001')
        self.assertIn('destinatario_fuera_entorno_demo',self.service.store.rules(case)['reasons'])
