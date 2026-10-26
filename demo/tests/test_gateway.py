from pathlib import Path
import sys,tempfile,unittest
from unittest.mock import patch
from starlette.testclient import TestClient
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from gateway import build_app
from cobranza import Store
from customer_service import CustomerService


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.service=CustomerService(Store(Path(self.tmp.name)/'test.sqlite'))
        self.app=build_app(self.service,'test-local-token-long-enough-1234')
    def tearDown(self):self.tmp.cleanup()
    def test_login_and_query(self):
        with TestClient(self.app) as c:
            self.assertEqual(c.post('/api/ask',json={'question':'saldo','dni':'74851236'}).status_code,401)
            self.assertEqual(c.post('/login',json={'password':'DemoAgentica!2026'}).status_code,200)
            with patch('gateway.ask_n8n',return_value={'answer':'Saldo PEN 1500.00','orchestrated_by':'n8n','execution_id':'123'}) as bridge:
                r=c.post('/api/ask',json={'question':'saldo','dni':'74851236'})
                bridge.assert_called_once()
            self.assertEqual(r.status_code,200);self.assertIn('1500.00',r.json()['answer'])
            self.assertEqual(c.post('/mail/claim',json={'reservation':'fake'}).status_code,401)
    def test_wrong_origin_and_host(self):
        with TestClient(self.app) as c:
            self.assertEqual(c.post('/login',json={'password':'DemoAgentica!2026'},headers={'Origin':'https://evil.example'}).status_code,403)
            self.assertEqual(c.get('/',headers={'Host':'evil.example'}).status_code,400)
    def test_mcp_requires_admin_bearer(self):
        with TestClient(self.app) as c:
            self.assertEqual(c.post('/mcp',json={}).status_code,401)
    def test_bad_login(self):
        with TestClient(self.app) as c:
            self.assertEqual(c.post('/login',json={'password':'wrong'}).status_code,401)
