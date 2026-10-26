import asyncio,os,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from codex_client import consultar_flujo
from mcp_server import create_mcp


class CodexClientTests(unittest.TestCase):
    def test_codex_profile_only_exposes_orchestrator(self):
        tools=asyncio.run(create_mcp(None,'codex').list_tools())
        self.assertEqual([t.name for t in tools],['consultar_orquestador'])
        self.assertIn('dni_seleccionado',tools[0].inputSchema['required'])
    def test_codex_calls_same_n8n_bridge(self):
        with patch.dict(os.environ,{'COBRANZA_TOKEN':'local-token-for-test'}),patch('codex_client.ask_n8n',return_value={'orchestrated_by':'n8n'}) as call:
            result=consultar_flujo('saldo DNI 40112233','74851236')
            call.assert_called_once_with('saldo DNI 40112233','74851236','local-token-for-test')
            self.assertEqual(result['orchestrated_by'],'n8n')
    def test_invalid_dni_stops_before_n8n(self):
        with patch('codex_client.ask_n8n') as call:
            with self.assertRaises(ValueError):consultar_flujo('saldo','123')
            call.assert_not_called()
