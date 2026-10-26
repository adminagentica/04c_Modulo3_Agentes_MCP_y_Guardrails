from pathlib import Path
import asyncio,concurrent.futures,json,sys,tempfile,unittest,uuid
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from cobranza import Store
from customer_service import CustomerService,MAILBOX,SUBJECT_PREFIX
from human_handoff import HandoffQueue
from web_orchestration import ChatOrchestrator
from mail_orchestration import MailOrchestrator
from team_mcp import TeamMcpSession
from gateway import build_app
from starlette.testclient import TestClient

class HumanHandoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.service=CustomerService(Store(Path(self.tmp.name)/'cases.sqlite'));self.service.seed()
        self.queue=HandoffQueue(self.service.store);self.chat=ChatOrchestrator(self.service);self.ident=str(uuid.uuid4())
    def tearDown(self):self.tmp.cleanup()
    def create(self,reason='solicitud_explicita',case_id='MAIL-DEMO-001'):
        return self.queue.create(self.ident,reason,case_id)
    def explicit(self,dni='74851236'):
        return self.chat.prepare('Quiero hablar con un ejecutivo humano',dni,self.ident)
    def test_explicit_request_uses_mcp_and_skips_llm_and_rag(self):
        with patch('web_orchestration.retrieve_passages') as rag:
            result=self.explicit()
        rag.assert_not_called();self.assertFalse(result['call_openai'])
        response=result['response'];ticket=response['human_handoff']
        self.assertEqual(ticket['status'],'pending');self.assertEqual(ticket['reason'],'solicitud_explicita')
        self.assertTrue(response['automation_paused']);self.assertFalse(response['email_sent'])
        self.assertIn('derivar_a_humano',[e['tool'] for e in response['agent_trace']])
        self.assertNotIn('redactor_respuesta',{e['agent_id'] for e in response['agent_trace']})
    def test_unknown_or_absent_client_has_no_debt_context(self):
        result=self.explicit('')['response'];ticket=result['human_handoff']
        self.assertFalse(ticket['context']['case_validated']);self.assertIsNone(ticket['case_id'])
        self.assertNotIn('balance_cents',ticket['context'])
    def test_conflicting_identity_is_not_attached_to_a_ticket(self):
        result=self.chat.prepare('Quiero hablar con un ejecutivo humano del DNI 40112233','74851236',self.ident)
        self.assertFalse(result['call_openai']);self.assertEqual(result['response']['state'],'clarify')
        self.assertEqual(self.queue.list(),[])
    def test_only_minimal_validated_context_is_stored(self):
        ticket=self.create();text=json.dumps(ticket['context'])
        self.assertNotIn('74851236',text);self.assertNotIn(MAILBOX,text);self.assertNotIn('question',text)
        self.assertEqual(ticket['context']['balance_cents'],150000);self.assertEqual(ticket['context']['case_version'],1)
    def test_creation_is_idempotent_for_request(self):
        first=self.create();second=self.create();self.assertEqual(first['id'],second['id']);self.assertEqual(len(self.queue.list()),1)
    def test_concurrent_claim_only_succeeds_once(self):
        ticket=self.create()
        def claim(_):
            try:self.queue.claim(ticket['id']);return True
            except ValueError:return False
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:self.assertEqual(sum(pool.map(claim,range(2))),1)
    def test_resolution_requires_claim_and_is_not_replayed(self):
        ticket=self.create()
        with self.assertRaises(ValueError):self.queue.resolve(ticket['id'],'revision_completada')
        self.queue.claim(ticket['id']);result=self.queue.resolve(ticket['id'],'revision_completada')
        self.assertEqual(result['status'],'resolved');self.assertFalse(result['resumed']);self.assertFalse(result['email_sent'])
        with self.assertRaises(ValueError):self.queue.resolve(ticket['id'],'revision_completada')
    def test_unknown_actor_or_send_decision_are_rejected(self):
        ticket=self.create()
        with self.assertRaises(ValueError):self.queue.claim(ticket['id'],'otro-actor')
        self.queue.claim(ticket['id'])
        with self.assertRaises(ValueError):self.queue.resolve(ticket['id'],'enviar_correo')
    def test_open_handoff_blocks_contact_and_close_requires_fresh_rules(self):
        self.assertTrue(self.service.reminder_eligibility('74851236')['can_prepare'])
        ticket=self.create();self.assertTrue(self.queue.is_blocking(ticket['case_id']))
        self.assertIn('revision_humana_pendiente',self.service.reminder_eligibility('74851236')['blocking_reasons'])
        self.queue.claim(ticket['id']);self.queue.resolve(ticket['id'],'revision_completada')
        self.assertFalse(self.queue.is_blocking(ticket['case_id']))
        with self.service.store.connect() as c:c.execute("UPDATE cases SET disputed=1 WHERE id='MAIL-DEMO-001'")
        self.assertFalse(self.service.reminder_eligibility('74851236')['can_prepare'])
    def test_keep_block_decision_does_not_release_contact(self):
        ticket=self.create();self.queue.claim(ticket['id']);result=self.queue.resolve(ticket['id'],'mantener_bloqueo')
        self.assertTrue(result['automation_paused']);self.assertTrue(self.queue.is_blocking(ticket['case_id']))
    def test_no_implicit_email_or_outbox_is_created(self):
        ticket=self.create();self.queue.claim(ticket['id']);self.queue.resolve(ticket['id'],'revision_completada')
        with self.service.store.connect() as c:
            self.assertEqual(c.execute('SELECT count(*) FROM outbox').fetchone()[0],0)
            self.assertEqual(c.execute('SELECT count(*) FROM email_inquiries').fetchone()[0],0)
            self.assertEqual(c.execute('SELECT count(*) FROM human_handoff_events').fetchone()[0],3)
        self.assertEqual(self.service.store.memory('demo','MAIL-DEMO-001')[-1]['payload']['decision'],'revision_completada')
    def test_missing_rag_creates_handoff_with_no_paid_call(self):
        with patch('web_orchestration.retrieve_passages',side_effect=OSError):
            result=self.chat.prepare('saldo y recordatorio','74851236',self.ident)
        self.assertFalse(result['call_openai']);ticket=result['response']['human_handoff']
        self.assertEqual(ticket['reason'],'evidencia_insuficiente');self.assertIn('1500',result['response']['answer'])
    def test_model_validation_failure_opens_human_review(self):
        self.chat.prepare('saldo','74851236',self.ident)
        invalid={'request_id':self.ident,'intro':'Consulta verificada contra las fuentes disponibles.','policy_answer':'Deuda inventada','citation_ids':[],'state':'answered'}
        provider={'output':[{'content':[{'type':'output_text','text':json.dumps(invalid)}]}]}
        with self.assertRaises(ValueError):self.chat.complete(self.ident,provider,200,'mock')
        self.assertEqual(self.queue.list()[0]['reason'],'fallo_validacion')
    def test_other_case_memory_and_scope_are_untouched(self):
        self.create();self.assertFalse(self.queue.is_blocking('MAIL-DEMO-002'))
        self.assertEqual(self.service.store.memory('demo','MAIL-DEMO-002'),[])
        with self.assertRaises(ValueError):self.queue.list('otro-tenant')
    def test_handoff_mcp_does_not_expose_resolution_to_models(self):
        async def inspect():
            async with TeamMcpSession(self.service,'',None,None,channel='handoff',handoff_scope={'request_id':self.ident,'case_id':None}) as session:
                tools=await session.session.list_tools();self.assertEqual([tool.name for tool in tools.tools],['derivar_a_humano'])
        asyncio.run(inspect())
    def test_pending_human_review_prevents_gmail_send_branch(self):
        self.create();mail=MailOrchestrator(self.service)
        message={'id':'1a1755a6233d8f84','from':MAILBOX,'subject':SUBJECT_PREFIX,'text':'Mi DNI es 74851236','labelIds':['INBOX','SENT']}
        result=mail.prepare(message)
        self.assertFalse(result['should_send']);self.assertEqual(result['state'],'needs_review')
        with self.service.store.connect() as c:self.assertEqual(c.execute("SELECT state FROM email_inquiries WHERE message_id=?",(message['id'],)).fetchone()[0],'prepared')
    def test_pending_handoff_blocks_a_previously_prepared_mail_claim(self):
        mail=MailOrchestrator(self.service)
        message={'id':'1a1755a6233d8f84','from':MAILBOX,'subject':SUBJECT_PREFIX,'text':'Mi DNI es 74851236','labelIds':['INBOX','SENT']}
        prepared=mail.prepare(message);self.create()
        with self.assertRaises(ValueError):mail.claim(prepared['reservation'])
        with self.service.store.connect() as c:self.assertEqual(c.execute('SELECT state FROM email_inquiries WHERE reservation=?',(prepared['reservation'],)).fetchone()[0],'prepared')
    def test_queue_api_is_authenticated_and_uses_fixed_demo_actor(self):
        ticket=self.create();token='isolated-demo-header-token-long-enough'
        with TestClient(build_app(self.service,token)) as client:
            self.assertEqual(client.get('/api/handoffs').status_code,401)
            self.assertEqual(client.post('/api/handoffs/claim',json={'id':ticket['id']}).status_code,401)
            client.post('/login',json={'password':'DemoAgentica!2026'})
            self.assertEqual(client.get('/api/handoffs').status_code,200)
            claimed=client.post('/api/handoffs/claim',json={'id':ticket['id'],'actor':'admin-inventado'})
            self.assertEqual(claimed.status_code,200);self.assertEqual(claimed.json()['assigned_to'],'ejecutivo-demo')
            result=client.post('/api/handoffs/resolve',json={'id':ticket['id'],'decision':'revision_completada'})
            self.assertEqual(result.status_code,200);self.assertFalse(result.json()['resumed'])

    def test_policy_about_human_review_is_not_an_explicit_transfer(self):
        rag={'index_version':'mock','citations':[{'id':3,'code':'POL-COB-04','version':'v4','section':'§3','content':'Revisión humana','sourceHash':'a'*64}]}
        with patch('web_orchestration.retrieve_passages',return_value=rag):
            result=self.chat.prepare('¿Qué política exige revisión humana?','',self.ident)
        self.assertTrue(result['call_openai']);self.assertEqual(self.queue.list(),[])
