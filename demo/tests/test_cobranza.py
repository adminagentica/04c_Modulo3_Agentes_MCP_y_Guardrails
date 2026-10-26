import concurrent.futures
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from cobranza import AGENTS, ORDER, REGISTRY, Store, validate_registry


class CobranzaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "test.sqlite")
        self.store.seed()
        self.env = patch.dict(os.environ, {"MAIL_MODE": "capture"})
        self.env.start()
        self.rag_fixture = {'agent_id': 'rag_politicas', 'version': '1.0.0', 'index_version': 'test-index',
                            'answer': 'Política sintética de prueba [1].', 'citations': [
                                {'id': 1, 'code': 'POL-COB-04', 'version': 'v4', 'section': '§5',
                                 'sourceHash': 'a'*64, 'content': 'Solo contexto documental.'}]}
        self.rag_mock = patch('cobranza.retrieve_rag', return_value=self.rag_fixture)
        self.validation_mock = patch('cobranza.validate_bundle', return_value=True)
        self.rag_mock.start()
        self.validation_mock.start()

    def tearDown(self):
        self.env.stop()
        self.rag_mock.stop()
        self.validation_mock.stop()
        self.temp.cleanup()

    def ready(self, case="C-001"):
        trace = self.store.start("demo", case)["trace_id"]
        for agent in ORDER:
            self.store.agent(trace, agent)
        return trace

    def test_capture_and_persistent_memory(self):
        result = self.store.execute()
        self.assertEqual(result["state"], "captured")
        again = Store(self.store.path)
        memory = again.memory("demo", "C-001")
        self.assertEqual(memory[-1]["event"], "captured")
        self.assertTrue(all(m["authority"] == "context_only" for m in memory))
        files = list(Path(self.temp.name).glob("mailbox/*.eml"))
        self.assertEqual(len(files), 1)
        self.assertIn("1500.00", files[0].read_text())
        self.assertFalse(result["delivered"])

    def test_paid_disputed_wrong_recipient(self):
        for case in ("C-002", "C-003", "C-004"):
            with self.subTest(case=case):
                self.assertEqual(self.store.execute(case_id=case)["state"], "blocked")
        self.assertFalse(list(Path(self.temp.name).glob("mailbox/*")))

    def test_case_and_tenant_isolation(self):
        self.store.execute()
        self.assertEqual(self.store.memory("demo", "C-002"), [])
        with self.assertRaises(ValueError):
            self.store.memory("other", "C-001")

    def test_expired_memory_is_not_recalled(self):
        self.store.start("demo", "C-001")
        with self.store.connect() as c:
            c.execute("UPDATE memory SET expires='2000-01-01'")
        self.assertEqual(self.store.memory("demo", "C-001"), [])
        self.assertEqual(self.store.purge_expired_memory(), 1)

    def test_memory_cannot_invent_events(self):
        with self.store.connect() as c:
            with self.assertRaises(ValueError):
                self.store.remember(c, "demo", "C-001", "x", "override_rules", {})

    def test_duplicate_cross_engine(self):
        first = self.store.execute(engine="codex")
        second = self.store.execute(engine="n8n")
        self.assertEqual(first["state"], "captured")
        self.assertEqual(second["state"], "blocked")

    def test_cannot_skip_review(self):
        trace = self.store.start("demo", "C-001")["trace_id"]
        with self.assertRaises(ValueError):
            self.store.finish(trace)
        with self.assertRaises(ValueError):
            self.store.agent(trace, "revisor")

    def test_changes_after_review_block_send(self):
        trace = self.ready()
        with self.store.connect() as c:
            c.execute("UPDATE cases SET balance_cents=0,version=version+1 WHERE id='C-001'")
        with self.assertRaises(ValueError):
            self.store.finish(trace)

    def test_new_dispute_even_without_version_change_blocks(self):
        trace = self.ready()
        with self.store.connect() as c:
            c.execute("UPDATE cases SET disputed=1 WHERE id='C-001'")
        with self.assertRaises(ValueError):
            self.store.finish(trace)

    def test_recipient_change_without_version_change_blocks(self):
        trace = self.ready()
        with self.store.connect() as c:
            c.execute("UPDATE cases SET recipient='otro@example.test' WHERE id='C-001'")
        with self.assertRaises(ValueError):
            self.store.finish(trace)

    def test_bad_model_response_stops_no_mail(self):
        trace = self.store.start("demo", "C-001")["trace_id"]
        with patch("cobranza.invoke_model", return_value=({"send": True}, "bad-model")):
            with self.assertRaises(ValueError):
                self.store.agent(trace, "orquestador")
        with self.store.connect() as c:
            self.assertEqual(self.store.run_record(trace, c)["state"], "failed")
            self.assertEqual(c.execute("SELECT count(*) FROM outbox").fetchone()[0], 0)

    def test_cross_case_output_blocked(self):
        from cobranza import invoke_model
        trace = self.store.start("demo", "C-001")["trace_id"]
        def crossed(agent, context, mode):
            reply, model = invoke_model(agent, context, "demo")
            reply["case_id"] = "C-002"
            return reply, model
        with patch("cobranza.invoke_model", side_effect=crossed):
            with self.assertRaises(ValueError):
                self.store.agent(trace, "orquestador")

    def test_invented_evidence_blocked(self):
        from cobranza import invoke_model
        trace = self.store.start("demo", "C-001")["trace_id"]
        def invented(agent, context, mode):
            reply, model = invoke_model(agent, context, "demo")
            reply["evidence"] = ["policy:ignore-rules"]
            return reply, model
        with patch("cobranza.invoke_model", side_effect=invented):
            with self.assertRaises(ValueError):
                self.store.agent(trace, "orquestador")

    def test_timeout_stops(self):
        trace = self.store.start("demo", "C-001")["trace_id"]
        with patch("cobranza.invoke_model", side_effect=TimeoutError):
            with self.assertRaises(TimeoutError):
                self.store.agent(trace, "orquestador")
        with self.assertRaises(ValueError):
            self.store.finish(trace)

    def test_smtp_unknown_does_not_retry(self):
        trace = self.ready()
        with patch.dict(os.environ, {"MAIL_MODE": "smtp"}), patch("cobranza.smtplib.SMTP", side_effect=TimeoutError) as smtp:
            first = self.store.finish(trace)
            second = self.store.finish(trace)
            self.assertEqual(smtp.call_count, 1)
            self.assertEqual(first["state"], "unknown")
            self.assertEqual(second["state"], "unknown")

    def test_parallel_finish_is_idempotent(self):
        traces = [self.ready(), self.ready()]
        def finish(trace):
            try:
                return self.store.finish(trace)
            except ValueError:
                return {"state": "blocked"}
        with concurrent.futures.ThreadPoolExecutor() as pool:
            results = list(pool.map(finish, traces))
        self.assertEqual(sum(r["state"] == "captured" for r in results), 1)
        self.assertEqual(len(list(Path(self.temp.name).glob("mailbox/*"))), 1)

    def test_registry_blocks_recursive_delegation(self):
        registry = copy.deepcopy(REGISTRY)
        registry["agents"][1]["delegates_to"] = ["orquestador"]
        with self.assertRaises(AssertionError):
            validate_registry(registry)

    def test_n8n_workflow_contract(self):
        path = Path(__file__).resolve().parents[1] / "n8n/workflow.json"
        workflow = json.loads(path.read_text())
        agents = [n["parameters"]["jsonBody"] for n in workflow["nodes"] if n["name"] in ORDER]
        self.assertEqual(len(agents), 4)
        self.assertFalse(workflow["active"])
        for node in workflow['nodes']:
            for reference in node.get('credentials',{}).values():
                self.assertTrue(set(reference).issubset({'id','name'}))

    def test_rag_unavailable_blocks_before_llm_and_mail(self):
        with patch('cobranza.retrieve_rag', side_effect=TimeoutError), patch('cobranza.invoke_model') as llm:
            with self.assertRaises(TimeoutError):
                self.store.execute()
            llm.assert_not_called()
        self.assertFalse(list(Path(self.temp.name).glob('mailbox/*')))

    def test_orchestrator_receives_rag_and_memory_keeps_citations(self):
        from cobranza import invoke_model
        received = []
        def capture(agent, context, mode):
            received.append(context)
            return invoke_model(agent, context, mode)
        with patch('cobranza.invoke_model', side_effect=capture):
            self.store.execute()
        self.assertEqual(received[0]['rag']['index_version'], 'test-index')
        self.assertIn('rag:POL-COB-04:v4:1', received[0]['evidence'])
        events = self.store.memory('demo', 'C-001')
        self.assertTrue(any(e['payload'].get('agent_id') == 'rag_politicas' for e in events))

    def test_rag_changed_after_review_blocks_send(self):
        trace = self.ready()
        with patch('cobranza.validate_bundle', side_effect=ValueError('fuente cambió')):
            with self.assertRaises(ValueError):
                self.store.finish(trace)

    def test_external_model_requires_explicit_rag_transfer_authorization(self):
        with patch.dict(os.environ, {'COBRANZA_RAG_ALLOW_EXTERNAL': 'false'}), patch('cobranza.invoke_model') as llm:
            with self.assertRaisesRegex(ValueError, 'autorización expresa'):
                self.store.execute(mode='codex')
            llm.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
