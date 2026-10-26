"""Supervisor ejecutable: delegación acotada, memoria, MCP y trazas por consulta."""
import asyncio
from pathlib import Path
import json
import re
from cobranza import stamp
from team_mcp import TeamMcpSession

TEAM_REGISTRY=json.loads((Path(__file__).resolve().parents[1]/'config/team.json').read_text())
VERSION=TEAM_REGISTRY['version']
TEAM={agent['id']:(agent['name'],agent['tools']) for agent in TEAM_REGISTRY['agents']}
AGENT_VERSIONS={agent['id']:agent['version'] for agent in TEAM_REGISTRY['agents']}


class AgentSupervisor:
    def __init__(self, service, request_id, retrieve, validate):
        self.service, self.request_id = service, request_id
        self.retrieve, self.validate = retrieve, validate
        with service.store.connect() as c:
            c.executescript('''
            CREATE TABLE IF NOT EXISTS team_runs(id TEXT PRIMARY KEY,state TEXT,case_id TEXT,created TEXT);
            CREATE TABLE IF NOT EXISTS team_events(id INTEGER PRIMARY KEY,request_id TEXT,agent_id TEXT,agent_version TEXT,
                phase TEXT,status TEXT,tool TEXT,created TEXT);
            CREATE INDEX IF NOT EXISTS team_events_request ON team_events(request_id,id);
            ''')

    def begin(self):
        with self.service.store.connect() as c:
            c.execute('INSERT INTO team_runs VALUES(?,?,?,?)', (self.request_id, 'preparing', None, stamp()))
        self.event('orquestador', 'input_guardrail', 'started')

    def event(self, agent, phase, status, tool=''):
        if agent not in TEAM or (tool and tool not in TEAM[agent][1]):
            raise ValueError('Derivación o herramienta no autorizada')
        with self.service.store.connect() as c:
            c.execute('INSERT INTO team_events(request_id,agent_id,agent_version,phase,status,tool,created) VALUES(?,?,?,?,?,?,?)',
                      (self.request_id, agent, AGENT_VERSIONS[agent], phase, status, tool, stamp()))

    async def delegate(self, session, agent, tool, args=None):
        self.event(agent, 'delegation', 'started', tool)
        try:
            result = await session.call(tool, args)
        except Exception:
            self.event(agent, 'delegation', 'failed', tool)
            raise
        self.event(agent, 'delegation', 'completed', tool)
        return result

    def collect(self, dni, account_intent, reminder_intent, policy, rag_question):
        async def run():
            account = snapshot = reminder = rag = None
            memory = {'scope': 'no_client', 'authority': 'context_only', 'events': []}
            async with TeamMcpSession(self.service, dni, self.retrieve, self.validate) as session:
                if account_intent:
                    customer = await self.delegate(session, 'analista_saldo', 'saldo_cliente')
                    if not customer['matched']:
                        return {'identity_valid': False}
                    account, snapshot = customer['account'], customer['fingerprint']
                    with self.service.store.connect() as c:
                        c.execute('UPDATE team_runs SET case_id=? WHERE id=?', (account['case_id'], self.request_id))
                    memory = await self.delegate(session, 'orquestador', 'recordar_contexto')
                if reminder_intent:
                    reminder = await self.delegate(session, 'analista_elegibilidad', 'evaluar_contacto')
                rag_failed = False
                if policy:
                    try:
                        rag = await self.delegate(session, 'rag_politicas', 'recuperar_politicas', {'pregunta': rag_question})
                    except Exception:
                        if not reminder_intent:
                            raise
                        rag_failed = True
            return {'identity_valid': True, 'account': account, 'fingerprint': snapshot,
                    'reminder': reminder, 'rag': rag, 'rag_failed': rag_failed, 'memory': memory}
        return asyncio.run(run())

    def prepared(self):
        self.event('orquestador', 'input_guardrail', 'passed')
        self.event('redactor_respuesta', 'llm_response', 'awaiting_n8n')
        with self.service.store.connect() as c:
            c.execute("UPDATE team_runs SET state='prepared' WHERE id=? AND state='preparing'", (self.request_id,))

    def claim_review(self):
        with self.service.store.connect() as c:
            claimed = c.execute("UPDATE team_runs SET state='reviewing' WHERE id=? AND state='prepared'", (self.request_id,)).rowcount
        if claimed != 1:
            raise ValueError('Consulta desconocida, en revisión o ya completada')

    def review(self, context, parsed):
        self.event('redactor_respuesta', 'llm_response', 'returned')
        self.event('revisor_respuesta', 'output_guardrail', 'started')
        validate_response(context, parsed)
        async def run():
            async with TeamMcpSession(self.service, context.get('selected_dni', ''), self.retrieve, self.validate) as session:
                if context['account']:
                    customer = await self.delegate(session, 'revisor_respuesta', 'saldo_cliente')
                    if not customer['matched']:
                        raise ValueError('La identidad dejó de ser válida')
                return await self.delegate(session, 'revisor_respuesta', 'verificar_contexto', {
                    'expected_fingerprint': context['case_fingerprint'] or '',
                    'bundle': context['rag'] or {}, 'check_contact': bool(context.get('reminder_check'))})
        result = asyncio.run(run())
        self.event('revisor_respuesta', 'output_guardrail', 'needs_review' if parsed['state']=='needs_review' else 'passed')
        return result

    def handoff(self,reason):
        with self.service.store.connect() as c:
            row=c.execute('SELECT case_id FROM team_runs WHERE id=?',(self.request_id,)).fetchone()
        scope={'request_id':self.request_id,'case_id':row['case_id'] if row else None}
        async def run():
            async with TeamMcpSession(self.service,'',None,None,channel='handoff',handoff_scope=scope) as session:
                return await self.delegate(session,'orquestador','derivar_a_humano',{'reason':reason})
        return asyncio.run(run())

    def finish(self, result):
        if result['state'] in {'needs_review','error'}:
            reason=result.pop('handoff_reason',None) or ('fallo_proveedor' if result['state']=='error' else
                    'regla_contacto' if result.get('reminder_check') and not result['reminder_check']['can_prepare'] else 'evidencia_insuficiente')
            result['human_handoff']=self.handoff(reason)
            result['automation_paused']=True
            if 'answer' in result:
                result['answer']+='\n\nDerivación humana registrada: '+result['human_handoff']['id']+'. Estado: pendiente de atención. No se envió ningún correo.'
        self.event('orquestador', 'final_response', result['state'])
        with self.service.store.connect() as c:
            row = c.execute('SELECT case_id FROM team_runs WHERE id=?', (self.request_id,)).fetchone()
            c.execute('UPDATE team_runs SET state=? WHERE id=?', (result['state'], self.request_id))
            if row and row['case_id']:
                payload = {'agent_id': 'orquestador', 'version': VERSION, 'status': result['state'],
                           'n8n_execution_id': result.get('execution_id'), 'reminder_sent': False}
                self.service.store.remember(c, 'demo', row['case_id'], self.request_id, 'agent_completed', payload)
        return self.enrich(result)

    def failed(self):
        self.event('orquestador', 'guardrail', 'failed')
        with self.service.store.connect() as c:
            c.execute("UPDATE team_runs SET state='failed' WHERE id=?", (self.request_id,))
            row=c.execute('SELECT case_id FROM team_runs WHERE id=?',(self.request_id,)).fetchone()
            if row and row['case_id']:
                self.service.store.remember(c,'demo',row['case_id'],self.request_id,'failed',
                                            {'agent_id':'orquestador','version':VERSION,'status':'failed'})

        with self.service.store.connect() as c:
            attempted=c.execute("SELECT 1 FROM team_events WHERE request_id=? AND agent_id<>'orquestador' LIMIT 1",(self.request_id,)).fetchone()
        if attempted:
            self.handoff('fallo_validacion')

    def enrich(self, result):
        with self.service.store.connect() as c:
            rows = c.execute('SELECT agent_id,agent_version,phase,status,tool FROM team_events WHERE request_id=? ORDER BY id', (self.request_id,)).fetchall()
        result.update(request_id=self.request_id, team_version=VERSION,
                      agent_trace=[{**dict(row), 'name': TEAM[row['agent_id']][0]} for row in rows],
                      mcp_transport='sdk_in_memory')
        result.setdefault('email_sent',False)
        return result


def validate_response(context, parsed):
    if set(parsed) != {'request_id', 'intro', 'policy_answer', 'citation_ids', 'state'} or parsed['request_id'] != context['request_id']:
        raise ValueError('Contrato de respuesta inválido')
    if parsed['state'] not in {'answered', 'needs_review', 'clarify'} or parsed['intro'] not in {
        'Consulta verificada contra las fuentes disponibles.', 'Necesito información adicional para responder.', 'La consulta requiere revisión del ejecutivo.'}:
        raise ValueError('Estado o introducción fuera de contrato')
    if not isinstance(parsed['policy_answer'], str) or len(parsed['policy_answer']) > 5000 or not isinstance(parsed['citation_ids'], list):
        raise ValueError('Respuesta inválida o excesiva')
    allowed = {x['id'] for x in context['rag']['citations']} if context['rag'] else set()
    if any(type(ident) != int or ident not in allowed for ident in parsed['citation_ids']):
        raise ValueError('Cita inventada')
    if not context['rag'] and (parsed['policy_answer'] or parsed['citation_ids']):
        raise ValueError('Texto documental sin evidencia')

    if context['rag'] and parsed['state']=='answered':
        used={int(ident) for ident in re.findall(r'\[(\d+)\]',parsed['policy_answer'])}
        if not used or not used.issubset(set(parsed['citation_ids'])):
            if context.get('reminder_check'):
                parsed.update(state='needs_review',citation_ids=[],policy_answer='')
            else:
                raise ValueError('Respuesta documental sin citas verificables')
