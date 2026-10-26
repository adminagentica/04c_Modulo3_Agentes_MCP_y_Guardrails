from pathlib import Path
import concurrent.futures
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from customer_service import CustomerService, MAILBOX, SUBJECT_PREFIX, email_address
from cobranza import Store


class InquiryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.service=CustomerService(Store(Path(self.tmp.name)/'cases.sqlite'))
        self.service.seed()

    def tearDown(self):self.tmp.cleanup()

    def mail(self, **overrides):
        return {**{'id':'1a1752c5275b2599','from':{'value':[{'address':MAILBOX}]},'subject':SUBJECT_PREFIX,
                   'text':'Deseo conocer mi deuda. DNI 74851236','labelIds':['SENT','INBOX'],'headers':{}},**overrides}

    def test_exact_balance_not_rag(self):
        with patch.object(self.service,'policies') as rag:
            r=self.service.ask('¿Cuál es el saldo?', '74851236')
            self.assertIn('1500.00',r['answer']);rag.assert_not_called()

    def test_email_identity_match(self):
        r=self.service.prepare_email(self.mail())
        self.assertTrue(r['identity_validated']);self.assertEqual(r['to'],MAILBOX)
        self.assertIn('1500.00',r['body']);self.assertNotIn('74851236',r['body'])

    def test_natural_language_dni(self):
        r=self.service.prepare_email(self.mail(text='Hola, mi DNI es 74851236. Deseo consultar mi deuda.'))
        self.assertTrue(r['identity_validated']);self.assertIn('1500.00',r['body'])

    def test_wrong_dni_returns_no_debt(self):
        for text in ['DNI 12345678','DNI 123','DNI 74851236 y DNI 40112233','sin documento']:
            with self.subTest(text=text):
                mail=self.mail(text=text,id='aabbccdd'+str(len(text)))
                r=self.service.prepare_email(mail)
                self.assertFalse(r['identity_validated']);self.assertNotIn('1500.00',r['body'])

    def test_wrong_email_or_spoofed_self_sender(self):
        for m in [self.mail(**{'from':'otro@example.com'}),self.mail(labelIds=['INBOX'])]:
            self.assertFalse(self.service.prepare_email(m)['should_send'])

    def test_db_email_mismatch(self):
        with self.service.store.connect() as c:c.execute("UPDATE inquiry_customers SET email='otro@example.test' WHERE dni='74851236'")
        r=self.service.prepare_email(self.mail())
        self.assertFalse(r['identity_validated']);self.assertNotIn('1500.00',r['body'])

    def test_duplicate_inbound_and_claim(self):
        r=self.service.prepare_email(self.mail())
        self.assertFalse(self.service.prepare_email(self.mail())['should_send'])
        self.service.claim(r['reservation'])
        with self.assertRaises(ValueError):self.service.claim(r['reservation'])

    def test_concurrent_claim_only_once(self):
        r=self.service.prepare_email(self.mail())
        def claim(_):
            try:self.service.claim(r['reservation']);return True
            except ValueError:return False
        with concurrent.futures.ThreadPoolExecutor() as p:self.assertEqual(sum(p.map(claim,range(2))),1)

    def test_confirm_real_gmail_id(self):
        r=self.service.prepare_email(self.mail());self.service.claim(r['reservation'])
        self.assertEqual(self.service.sent(r['reservation'],'1a1752c5275b2600')['state'],'gmail_accepted')

    def test_prevent_email_loop(self):
        self.assertFalse(self.service.prepare_email(self.mail(subject='Respuesta de deuda · DEMO Agentica'))['should_send'])
        self.assertFalse(self.service.prepare_email(self.mail(headers={'in-reply-to':'abc'}))['should_send'])

    def test_zero_balance_query(self):
        self.assertEqual(self.service.balance('40112233')['balance'],'0.00')

    def test_policies_use_rag(self):
        expected={'route':'rag','state':'answered','answer':'Regla [1]','citations':[]}
        with patch.object(self.service,'policies',return_value=expected) as rag:
            self.assertEqual(self.service.ask('¿Qué política aplica?')['route'],'rag');rag.assert_called_once()

    def test_mixed_question(self):
        with patch.object(self.service,'policies',return_value={'route':'rag','state':'answered','answer':'Regla','citations':[]}):
            r=self.service.ask('¿Cuál es el saldo y qué política aplica?', '74851236')
            self.assertEqual(r['route'],'account+rag');self.assertIn('1500.00',r['answer'])

    def test_conflicting_dni_no_data(self):
        r=self.service.ask('Saldo del DNI 40112233','74851236')
        self.assertEqual(r['state'],'clarify');self.assertNotIn('account',r)

    def test_email_header_injection_rejected(self):
        for bad in ['a@b.com\nBcc: victim@b.com','a@b.com,b@b.com','invalid']:
            with self.assertRaises(ValueError):email_address(bad)

    def test_changed_balance_blocks_before_send(self):
        r=self.service.prepare_email(self.mail())
        with self.service.store.connect() as c:c.execute("UPDATE cases SET balance_cents=0 WHERE id='MAIL-DEMO-001'")
        with self.assertRaises(ValueError):self.service.claim(r['reservation'])

    def test_document_code_is_policy_intent(self):
        with patch.object(self.service,'policies',return_value={'route':'rag','state':'answered','answer':'Regla','citations':[]}) as rag:
            self.assertEqual(self.service.ask('¿Qué controles exige POL-COB-04?')['route'],'rag')
            rag.assert_called_once()

    def test_echoed_rag_answer_requires_review(self):
        question='¿Qué política aplica?'
        citation={'id':1,'code':'POL-COB-04','version':'v4','section':'§5','content':'Validar contacto antes de actuar.','sourceHash':'a'*64}
        with patch('customer_service.rag_request',side_effect=[{'indexVersion':'i'}, {'answer':question,'insufficientEvidence':False,'citations':[citation]}]), patch('customer_service.validate_bundle',return_value=True):
            r=self.service.policies(question)
            self.assertEqual(r['state'],'needs_review');self.assertEqual(r['method'],'extractive_review_required')
