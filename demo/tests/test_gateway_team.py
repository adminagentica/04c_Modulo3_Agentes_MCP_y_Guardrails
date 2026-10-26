from pathlib import Path
import json,sys,tempfile,unittest
from unittest.mock import patch
from starlette.testclient import TestClient
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from cobranza import Store
from customer_service import CustomerService,MAILBOX,SUBJECT_PREFIX
from gateway import build_app

class GatewayTeamTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.service=CustomerService(Store(Path(self.tmp.name)/'cases.sqlite'))
        self.token='isolated-local-token-at-least-24-characters'
        self.app=build_app(self.service,self.token)
    def tearDown(self):self.tmp.cleanup()
    def test_app_bridge_preserves_full_supervisor_trace(self):
        rag={'index_version':'mock','citations':[{'id':3,'code':'POL-COB-04','version':'v4','section':'§3','content':'Condiciones de contacto.','sourceHash':'a'*64}]}
        headers={'Authorization':'Bearer '+self.token}
        with TestClient(self.app) as client:
            client.post('/login',json={'password':'DemoAgentica!2026'})
            def simulated_n8n(question,dni,token):
                self.assertEqual(token,self.token)
                context=client.post('/chat/context',json={'question':question,'dni':dni,'request_id':'89908be2-bb55-48af-a315-f230a7548a03'},headers=headers)
                self.assertEqual(context.status_code,200)
                prepared=context.json();self.assertTrue(prepared['call_openai'])
                structured={'request_id':prepared['request_id'],'intro':'Consulta verificada contra las fuentes disponibles.','policy_answer':'Revisar condiciones [3].','citation_ids':[3],'state':'answered'}
                provider={'model':'mock-no-api','output':[{'content':[{'type':'output_text','text':json.dumps(structured)}]}]}
                result=client.post('/chat/result',json={'request_id':prepared['request_id'],'openai_response':provider,'openai_status':200,'execution_id':'simulated-n8n'},headers=headers)
                self.assertEqual(result.status_code,200);return result.json()
            with patch('gateway.ask_n8n',side_effect=simulated_n8n),patch('web_orchestration.retrieve_passages',return_value=rag),patch('web_orchestration.validate_bundle',return_value=True):
                response=client.post('/api/ask',json={'question':'saldo y recordatorio','dni':'74851236'})
            self.assertEqual(response.status_code,200);result=response.json()
            self.assertEqual(result['team_version'],'1.2.0');self.assertFalse(result['email_sent'])
            self.assertIn('revisor_respuesta',{e['agent_id'] for e in result['agent_trace']})
            self.assertIn('1500.00',result['answer'])
    def test_mail_prepare_uses_same_supervisor_and_keeps_session_blocked(self):
        message={'id':'1a1755a6233d8f84','from':MAILBOX,'subject':SUBJECT_PREFIX,'text':'Mi DNI es 74851236','labelIds':['INBOX','SENT']}
        with TestClient(self.app) as client:
            client.post('/login',json={'password':'DemoAgentica!2026'})
            self.assertEqual(client.post('/mail/prepare',json=message).status_code,401)
            response=client.post('/mail/prepare',json=message,headers={'Authorization':'Bearer '+self.token})
            self.assertEqual(response.status_code,200);result=response.json()
            self.assertTrue(result['should_send']);self.assertFalse(result['email_sent'])
            self.assertEqual(result['mcp_transport'],'sdk_in_memory')
            self.assertIn('gestor_correo',{e['agent_id'] for e in result['agent_trace']})
