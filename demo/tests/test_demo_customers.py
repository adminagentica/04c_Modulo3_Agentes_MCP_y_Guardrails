from pathlib import Path
import sys,tempfile,unittest,uuid,json,datetime as dt
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from cobranza import Store
from customer_service import CustomerService,MAILBOX,SUBJECT_PREFIX
from web_orchestration import ChatOrchestrator,focus_contact_citations
class DemoCustomerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.service=CustomerService(Store(Path(self.tmp.name)/'cases.sqlite'));self.service.seed()
    def tearDown(self):self.tmp.cleanup()
    def test_eligible_customer_has_verified_operational_controls(self):
        account=self.service.balance('71425836');check=self.service.reminder_eligibility('71425836')
        self.assertEqual(account['balance'],'850.00');self.assertEqual(account['email'],MAILBOX)
        self.assertTrue(check['can_prepare']);self.assertTrue(check['controls_verified']);self.assertEqual(check['days_overdue'],5)
        self.assertTrue(check['requires_explicit_confirmation']);self.assertFalse(check['sent'])
    def test_blocked_customer_stops_before_model_with_exact_policy(self):
        citation={'id':11,'code':'POL-PAG-02','version':'v5','section':'§4 Conciliación','content':'Pausar el contacto y derivar a Operaciones.','sourceHash':'a'*64}
        with patch('web_orchestration.retrieve_passages',return_value={'index_version':'mock','citations':[citation]}):
            result=ChatOrchestrator(self.service).prepare('saldo y recordatorio de pago','72536914',str(uuid.uuid4()))
        self.assertFalse(result['call_openai']);answer=result['response']
        self.assertIn('pago pendiente de conciliación',answer['answer']);self.assertEqual(answer['citations'],[citation])
        self.assertEqual(answer['human_handoff']['reason'],'regla_contacto');self.assertFalse(answer['email_sent'])
    def test_unknown_history_promises_and_special_flags_cannot_pass(self):
        for field in ['pending_payment','broken_promise','special_attention']:
            with self.service.store.connect() as c:c.execute(f"UPDATE inquiry_contact_controls SET {field}=1 WHERE case_id='MAIL-DEMO-APTO-001'")
            self.assertFalse(self.service.reminder_eligibility('71425836')['can_prepare'])
            with self.service.store.connect() as c:c.execute(f"UPDATE inquiry_contact_controls SET {field}=0 WHERE case_id='MAIL-DEMO-APTO-001'")
        with self.service.store.connect() as c:c.execute("UPDATE inquiry_contact_controls SET payment_history_checked=0 WHERE case_id='MAIL-DEMO-APTO-001'")
        self.assertIn('historial_no_verificado',self.service.reminder_eligibility('71425836')['blocking_reasons'])
    def test_more_than_thirty_days_cannot_pass(self):
        old=(dt.datetime.now(dt.timezone.utc).date()-dt.timedelta(days=31)).isoformat()
        with self.service.store.connect() as c:c.execute("UPDATE cases SET due=? WHERE id='MAIL-DEMO-APTO-001'",(old,))
        self.assertIn('fuera_gestion_temprana',self.service.reminder_eligibility('71425836')['blocking_reasons'])
    def test_seed_preserves_existing_case_and_control_changes(self):
        with self.service.store.connect() as c:c.execute("UPDATE inquiry_contact_controls SET pending_payment=1 WHERE case_id='MAIL-DEMO-APTO-001'")
        self.service.seed();self.assertFalse(self.service.reminder_eligibility('71425836')['can_prepare'])
    def test_eligible_customer_can_prepare_validated_gmail_reply_but_no_mail_sent(self):
        message={'id':'1a1755a6233d8f99','from':MAILBOX,'subject':SUBJECT_PREFIX,'text':'Mi DNI es 71425836','labelIds':['INBOX','SENT']}
        result=self.service.prepare_email(message);self.assertTrue(result['should_send']);self.assertTrue(result['identity_validated']);self.assertIn('850.00',result['body'])
    def test_contact_citations_are_relevant_and_maximum_three(self):
        citations=[{'id':i,'code':'POL-COB-04','section':f'§{i} Título'} for i in [1,2,3,4,5,6,7]]
        packed=focus_contact_citations({'citations':citations},{'blocking_reasons':[]})
        self.assertEqual([c['id'] for c in packed['citations']],[3,5,6])
    def test_response_only_lists_citations_used_in_answer(self):
        citations=[{'id':i,'code':'POL-COB-04','version':'v4','section':f'§{i} Título','content':'Texto','sourceHash':'a'*64} for i in [3,5,6]]
        chat=ChatOrchestrator(self.service);ident=str(uuid.uuid4())
        with patch('web_orchestration.retrieve_passages',return_value={'index_version':'mock','citations':citations}):prepared=chat.prepare('saldo y recordatorio','71425836',ident)
        self.assertEqual(len(json.loads(prepared['openai_payload']['input'])['passages']),3)
        value={'request_id':ident,'intro':'Consulta verificada contra las fuentes disponibles.','policy_answer':'Revisión humana [5].','citation_ids':[3,5,6],'state':'answered'}
        response={'output':[{'content':[{'type':'output_text','text':json.dumps(value)}]}]}
        with patch('web_orchestration.validate_bundle',return_value=True):result=chat.complete(ident,response,200,'mock')
        self.assertEqual([citation['id'] for citation in result['citations']],[5])
