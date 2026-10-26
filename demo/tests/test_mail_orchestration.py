from pathlib import Path
import asyncio,sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from cobranza import Store
from customer_service import CustomerService,MAILBOX,SUBJECT_PREFIX
from mail_orchestration import MailOrchestrator
from team_mcp import TeamMcpSession

class MailOrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.service=CustomerService(Store(Path(self.tmp.name)/'cases.sqlite'));self.service.seed()
        self.mail=MailOrchestrator(self.service)
        self.message={'id':'1a1755a6233d8f84','from':MAILBOX,'subject':SUBJECT_PREFIX,'text':'Mi DNI es 74851236','labelIds':['INBOX','SENT']}
    def tearDown(self):self.tmp.cleanup()
    def test_mail_phases_share_supervisor_trace_and_mcp_without_llm(self):
        prepared=self.mail.prepare(self.message);claimed=self.mail.claim(prepared['reservation'])
        self.assertEqual(prepared['request_id'],claimed['request_id']);self.assertEqual(claimed['state'],'sending')
        self.assertFalse(prepared['email_sent']);self.assertFalse(claimed['email_sent'])
        # Confirmación sintética: no existe llamada de red ni Gmail Send en este código.
        accepted=self.mail.sent(prepared['reservation'],'1a1755a9466a84df')
        self.assertEqual(accepted['request_id'],prepared['request_id']);self.assertEqual(accepted['state'],'gmail_accepted')
        self.assertEqual({e['agent_id'] for e in accepted['agent_trace']},{'orquestador','gestor_correo'})
    def test_wrong_sender_is_rejected_without_case_memory(self):
        result=self.mail.prepare({**self.message,'from':'otro@example.test'})
        self.assertFalse(result['should_send']);self.assertEqual(result['state'],'rejected')
        self.assertEqual(self.service.store.memory('demo','MAIL-DEMO-001'),[])
    def test_duplicate_does_not_repeat_prepare_or_send(self):
        first=self.mail.prepare(self.message);second=self.mail.prepare(self.message)
        self.assertTrue(first['should_send']);self.assertFalse(second['should_send']);self.assertEqual(second['state'],'duplicate')
    def test_repeat_claim_and_confirmation_are_blocked(self):
        prepared=self.mail.prepare(self.message);self.mail.claim(prepared['reservation'])
        with self.assertRaises(ValueError):self.mail.claim(prepared['reservation'])
        self.mail.sent(prepared['reservation'],'1a1755a9466a84df')
        with self.assertRaises(ValueError):self.mail.sent(prepared['reservation'],'1a1755a9466a84df')
    def test_mail_tools_do_not_expose_chat_or_llm_tools(self):
        async def inspect():
            async with TeamMcpSession(self.service,'',None,None,channel='mail') as session:
                tools=await session.session.list_tools()
                self.assertEqual({t.name for t in tools.tools},{'preparar_consulta_correo','reservar_respuesta_correo','confirmar_envio_correo'})
        asyncio.run(inspect())
