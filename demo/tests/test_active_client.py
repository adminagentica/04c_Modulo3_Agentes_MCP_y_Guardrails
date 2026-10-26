from pathlib import Path
import json,sqlite3,tempfile,unittest,uuid,sys
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from cobranza import Store
from customer_service import CustomerService
from conversation_memory import ConversationMemory
from web_orchestration import ChatOrchestrator
import test_conversation_reminders as reminder_helpers

class ActiveClientTests(unittest.TestCase):
    setUp=reminder_helpers.ConversationReminderTests.setUp
    tearDown=reminder_helpers.ConversationReminderTests.tearDown
    draft=reminder_helpers.ConversationReminderTests.draft
    confirm=reminder_helpers.ConversationReminderTests.confirm
    claim=reminder_helpers.ConversationReminderTests.claim
    accepted=reminder_helpers.ConversationReminderTests.accepted
    def test_explicit_dni_overrides_stale_selector_and_persists(self):
        p=self.chat.prepare('saldo de 71425836','74851236',str(uuid.uuid4()),self.conv)
        self.assertTrue(p['call_openai']);self.assertEqual(p['selected_dni'],'71425836')
        self.assertEqual(self.memory.active_client(self.conv),'71425836')
        nextp=self.chat.prepare('¿y el vencimiento?','',str(uuid.uuid4()),self.conv)
        self.assertEqual(json.loads(nextp['openai_payload']['input'])['account']['balance'],'850.00')
    def test_no_dni_or_context_requests_identity_without_llm(self):
        p=self.chat.prepare('cual es el saldo','',str(uuid.uuid4()),self.conv)
        self.assertFalse(p['call_openai']);self.assertIn('Indica el DNI',p['response']['answer'])
    def test_multiple_dnis_preserve_existing_context_and_draft(self):
        first=self.draft()
        p=self.chat.prepare('saldo de 74851236 y 71425836','',str(uuid.uuid4()),self.conv)
        self.assertFalse(p['call_openai']);self.assertEqual(self.memory.active_client(self.conv),'71425836')
        self.assertEqual(self.actions.pending(self.conv)['state'],'draft')
    def test_followup_reminder_uses_active_customer_without_selector(self):
        self.chat.prepare('saldo 71425836','',str(uuid.uuid4()),self.conv)
        p=self.chat.prepare('¿puedo mandarle un recordatorio?','',str(uuid.uuid4()),self.conv)
        data=json.loads(p['openai_payload']['input']);self.assertEqual(data['account']['balance'],'850.00');self.assertTrue(data['reminder_check']['can_prepare'])
    def test_customer_switch_invalidates_draft_even_after_returning(self):
        self.draft();old=self.displayed
        self.chat.prepare('saldo de 74851236','',str(uuid.uuid4()),self.conv)
        self.assertEqual(self.actions.pending(self.conv)['state'],'superseded')
        self.chat.prepare('saldo de 71425836','',str(uuid.uuid4()),self.conv)
        result=self.confirm(dni='');self.assertNotIn('dispatch_requested',result)
    def test_switch_after_approval_prevents_claim(self):
        self.draft();approved=self.confirm(dni='')
        self.chat.prepare('saldo 74851236','',str(uuid.uuid4()),self.conv)
        self.assertFalse(self.claim(approved)['should_send'])
    def test_refresh_and_other_conversation_isolate_active_client(self):
        self.chat.prepare('saldo 71425836','',str(uuid.uuid4()),self.conv)
        self.assertEqual(ConversationMemory(self.service.store).active_client(self.conv),'71425836')
        self.assertEqual(self.memory.active_client(self.memory.ensure()),'')
    def test_response_for_previous_client_cannot_complete_after_switch(self):
        ident=str(uuid.uuid4());self.chat.prepare('saldo 71425836','',ident,self.conv)
        self.chat.prepare('saldo 74851236','',str(uuid.uuid4()),self.conv)
        with self.assertRaises(ValueError):self.chat.complete(ident,{},200,'mock')
    def test_original_schema_migrates_without_losing_turns(self):
        with tempfile.TemporaryDirectory() as t:
            store=Store(Path(t)/'old.sqlite')
            with store.connect() as c:c.execute('CREATE TABLE chat_conversations(id TEXT PRIMARY KEY,actor TEXT,created TEXT,expires TEXT)')
            mem=ConversationMemory(store);ident=mem.ensure();mem.select_client(ident,'71425836');self.assertEqual(mem.active_client(ident),'71425836')

