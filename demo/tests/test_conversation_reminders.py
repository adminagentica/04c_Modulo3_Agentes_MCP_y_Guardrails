from pathlib import Path
import concurrent.futures,json,sys,tempfile,unittest,uuid,datetime as dt
from unittest.mock import patch
from starlette.testclient import TestClient
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from cobranza import Store
from customer_service import CustomerService,MAILBOX
from web_orchestration import ChatOrchestrator
from conversation_memory import ConversationMemory
from reminder_actions import ReminderActions
from reminder_orchestration import ReminderOrchestrator
from gateway import build_app
from mcp_server import create_mcp
import asyncio

class ConversationReminderTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.service=CustomerService(Store(Path(self.tmp.name)/'cases.sqlite'));self.service.seed()
        self.chat=ChatOrchestrator(self.service);self.memory=ConversationMemory(self.service.store);self.conv=self.memory.ensure();self.displayed=None
        self.actions=ReminderActions(self.service,lambda bundle:True);self.delivery=ReminderOrchestrator(self.service)
        self.rag={'index_version':'mock','citations':[{'id':3,'code':'POL-COB-04','version':'v4','section':'§3','content':'Controles de contacto','sourceHash':'a'*64}]}
        self.patches=[patch('web_orchestration.retrieve_passages',return_value=self.rag),patch('web_orchestration.validate_bundle',return_value=True),patch('reminder_orchestration.validate_bundle',return_value=True)]
        for p in self.patches:p.start()
    def tearDown(self):
        for p in self.patches:p.stop()
        self.tmp.cleanup()
    def draft(self):
        ident=str(uuid.uuid4());prepared=self.chat.prepare('saldo y recordatorio','71425836',ident,self.conv);self.assertTrue(prepared['call_openai'])
        data={'request_id':ident,'intro':'Consulta verificada contra las fuentes disponibles.','policy_answer':'Revisar el contacto [3].','citation_ids':[3],'state':'answered'}
        provider={'model':'mock-no-api','output':[{'content':[{'type':'output_text','text':json.dumps(data)}]}]}
        result=self.chat.complete(ident,provider,200,'mock-prepare');self.displayed=result['draft']['id'];return result
    def confirm(self,text='Envíalo',dni='71425836',conv=None):
        prepared=self.chat.prepare(text,dni,str(uuid.uuid4()),conv or self.conv,self.displayed);self.assertFalse(prepared['call_openai']);return prepared['response']
    def claim(self,response):return self.delivery.claim(response['conversation_id'],response['confirmation_request_id'],response['draft_id'])
    def accepted(self,response,gmail_id='1a1755a9466a84ff'):
        return self.delivery.result(response['conversation_id'],response['confirmation_request_id'],response['draft_id'],gmail_id,'mock-send')
    def test_first_question_creates_real_draft_and_only_second_confirmation_can_dispatch(self):
        first=self.draft();self.assertEqual(first['draft']['state'],'draft');self.assertEqual(first['draft']['recipient'],MAILBOX)
        self.assertIn('850.00',first['draft']['body']);self.assertIn('¿Confirmas',first['answer']);self.assertFalse(first['email_sent'])
        with self.service.store.connect() as c:self.assertEqual(c.execute('SELECT count(*) FROM outbox').fetchone()[0],0)
        approved=self.confirm();self.assertTrue(approved['dispatch_requested']);self.assertFalse(approved['email_sent'])
        claim=self.claim(approved);self.assertEqual(claim['to'],MAILBOX)
        final=self.accepted(approved);self.assertTrue(final['email_sent']);self.assertEqual(final['gmail_id'],'1a1755a9466a84ff')
        history=self.memory.history(self.conv);self.assertEqual(len(history),4);self.assertIn('Gmail aceptó',history[-1]['content'])
    def test_envialo_without_draft_never_dispatches(self):
        self.assertNotIn('dispatch_requested',self.confirm());self.assertEqual(self.actions.pending(self.conv),None)
    def test_other_conversation_cannot_access_draft(self):
        self.draft();other=self.memory.ensure();result=self.confirm(conv=other)
        self.assertNotIn('dispatch_requested',result);self.assertEqual(self.actions.pending(other),None)
    def test_customer_switch_requires_new_review(self):
        self.draft();response=self.confirm(dni='74851236');self.assertEqual(response['state'],'clarify');self.assertNotIn('dispatch_requested',response)
    def test_redirect_message_is_not_confirmation(self):
        self.draft();response=self.confirm('Envíalo a otra@example.test')
        self.assertNotIn('dispatch_requested',response);self.assertEqual(self.actions.pending(self.conv)['state'],'draft')
    def test_negated_or_ambiguous_confirmation_cannot_send(self):
        self.draft()
        for text in ['No confirmo el envío','¿qué significa envíalo?','tal vez luego']:
            self.assertNotIn('dispatch_requested',self.confirm(text))
    def test_cancellation_prevents_send(self):
        self.draft();self.confirm('Cancela el borrador');self.assertEqual(self.actions.pending(self.conv)['state'],'cancelled')
        self.assertNotIn('dispatch_requested',self.confirm())
    def test_expired_draft_requires_new_preparation(self):
        result=self.draft()
        with self.service.store.connect() as c:c.execute("UPDATE reminder_drafts SET expires=? WHERE id=?",((dt.datetime.now(dt.timezone.utc)-dt.timedelta(minutes=1)).isoformat(),result['draft']['id']))
        self.assertNotIn('dispatch_requested',self.confirm())
    def test_changed_balance_stops_approval(self):
        self.draft()
        with self.service.store.connect() as c:c.execute("UPDATE cases SET balance_cents=1 WHERE id='MAIL-DEMO-APTO-001'")
        self.assertNotIn('dispatch_requested',self.confirm())
    def test_new_block_between_approval_and_claim_stops_send(self):
        self.draft();approved=self.confirm()
        with self.service.store.connect() as c:c.execute("UPDATE inquiry_contact_controls SET pending_payment=1 WHERE case_id='MAIL-DEMO-APTO-001'")
        self.assertFalse(self.claim(approved)['should_send'])
        with self.service.store.connect() as c:self.assertEqual(c.execute('SELECT count(*) FROM outbox').fetchone()[0],0)
    def test_invalid_sources_stop_approval(self):
        self.draft()
        with patch('web_orchestration.validate_bundle',side_effect=ValueError('changed')):result=self.confirm()
        self.assertNotIn('dispatch_requested',result)
    def test_duplicate_confirmation_does_not_dispatch_twice(self):
        self.draft();first=self.confirm();second=self.confirm()
        self.assertTrue(first['dispatch_requested']);self.assertNotIn('dispatch_requested',second)
        self.claim(first);self.accepted(first);third=self.confirm();self.assertIn('ya fue enviado',third['answer']);self.assertNotIn('dispatch_requested',third)
    def test_two_concurrent_claims_only_reserve_one_email(self):
        self.draft();approved=self.confirm()
        def claim(_):
            try:return self.claim(approved)['should_send']
            except ValueError:return False
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:self.assertEqual(sum(pool.map(claim,range(2))),1)
        with self.service.store.connect() as c:self.assertEqual(c.execute('SELECT count(*) FROM outbox').fetchone()[0],1)
    def test_unknown_gmail_result_never_retries(self):
        self.draft();approved=self.confirm();self.claim(approved);result=self.accepted(approved,None)
        self.assertFalse(result['email_sent']);self.assertEqual(self.actions.pending(self.conv)['state'],'unknown')
        self.assertNotIn('dispatch_requested',self.confirm())
    def test_no_confirmation_turn_cannot_approve_directly(self):
        self.draft()
        with self.assertRaises(ValueError):self.actions.approve(self.conv,str(uuid.uuid4()),'71425836')
    def test_preview_must_have_been_recorded_before_approval(self):
        draft=self.actions.create(self.conv,str(uuid.uuid4()),'71425836',self.rag);request=str(uuid.uuid4());self.memory.add(self.conv,request,'user','Envíalo')
        result=self.actions.approve(self.conv,request,'71425836',draft['id']);self.assertNotIn('dispatch_requested',result)
    def test_message_mutation_invalidates_approval(self):
        draft=self.draft()['draft']
        with self.service.store.connect() as c:c.execute('UPDATE reminder_drafts SET recipient=? WHERE id=?',('otro@example.test',draft['id']))
        self.assertNotIn('dispatch_requested',self.confirm())
    def test_claim_without_approval_is_denied(self):
        draft=self.draft()['draft']
        with self.assertRaises(ValueError):self.actions.claim(self.conv,str(uuid.uuid4()),draft['id'])
    def test_sent_invoice_cannot_get_another_reminder(self):
        self.draft();approved=self.confirm();self.claim(approved);self.accepted(approved)
        result=self.chat.prepare('saldo y recordatorio','71425836',str(uuid.uuid4()),self.conv)
        self.assertFalse(result['call_openai']);self.assertFalse(result['response']['reminder_check']['can_prepare'])
    def test_draft_survives_new_orchestrator_instance(self):
        self.draft();self.chat=ChatOrchestrator(self.service);self.assertTrue(self.confirm()['dispatch_requested'])
    def test_public_mcp_exposes_conversation_but_not_delivery_tools(self):
        tools=asyncio.run(create_mcp(None,'codex').list_tools());self.assertEqual(len(tools),1)
        self.assertIn('conversation_id',tools[0].inputSchema['properties'])
    def test_signed_cookie_restores_same_conversation_and_blocks_delivery_endpoints(self):
        token='local-test-secret-token-long-enough'
        app=build_app(self.service,token)
        with TestClient(app) as client:
            self.assertEqual(client.get('/api/conversation').status_code,401)
            client.post('/login',json={'password':'DemoAgentica!2026'});first=client.get('/api/conversation').json()['conversation_id']
            self.memory.add(first,str(uuid.uuid4()),'user','Una pregunta de prueba')
            self.assertEqual(client.get('/api/conversation').json()['turns'][0]['content'],'Una pregunta de prueba')
            client.post('/login',json={'password':'DemoAgentica!2026'});self.assertEqual(client.get('/api/conversation').json()['conversation_id'],first)
            self.assertEqual(client.post('/reminder/claim',json={}).status_code,401)
            client.cookies.set('agentica_conversation',self.conv+'.firma-invalida')
            self.assertNotEqual(client.get('/api/conversation').json()['conversation_id'],self.conv)

    def test_confirmation_cannot_approve_a_draft_not_displayed_in_this_turn(self):
        first=self.draft()['draft']['id'];second=self.draft()['draft']['id']
        self.assertNotEqual(first,second)
        result=self.chat.prepare('Envíalo','71425836',str(uuid.uuid4()),self.conv,first)
        self.assertFalse(result['call_openai']);self.assertNotIn('dispatch_requested',result['response'])
        result=self.chat.prepare('Envíalo','71425836',str(uuid.uuid4()),self.conv)
        self.assertNotIn('dispatch_requested',result['response'])
