"""El mismo supervisor coordina el canal Gmail; el envío físico permanece en n8n."""
import asyncio
import sqlite3
import uuid
from agent_team import AgentSupervisor
from team_mcp import TeamMcpSession
from human_handoff import HandoffQueue


class MailOrchestrator:
    def __init__(self, service):
        self.service = service

    def team(self, message_id):
        request_id = str(uuid.uuid5(uuid.NAMESPACE_URL, 'agentica:mail:' + message_id))
        return AgentSupervisor(self.service, request_id, None, None)

    def reservation_team(self, reservation):
        with self.service.store.connect() as c:
            row = c.execute('SELECT message_id FROM email_inquiries WHERE reservation=?', (reservation,)).fetchone()
        if not row:
            raise ValueError('Reserva desconocida')
        return self.team(row['message_id'])

    def invoke(self, team, tool, arguments):
        async def run():
            async with TeamMcpSession(self.service, '', None, None, channel='mail') as session:
                return await team.delegate(session, 'gestor_correo', tool, arguments)
        return asyncio.run(run())

    def prepare(self, message):
        message_id = message.get('id', '')
        if not isinstance(message_id, str) or not 8 <= len(message_id) <= 64:
            raise ValueError('Se requiere ID del mensaje Gmail')
        team = self.team(message_id)
        try:
            team.begin()
        except sqlite3.IntegrityError:
            return team.enrich({'state': 'duplicate', 'should_send': False})
        try:
            result = self.invoke(team, 'preparar_consulta_correo', {'mensaje': message})
            if result.get('identity_validated') and result.get('_case_id'):
                self.service.store.case('demo', result['_case_id'])
                with self.service.store.connect() as c:
                    c.execute('UPDATE team_runs SET case_id=? WHERE id=?', (result['_case_id'], team.request_id))
            if result.get('_case_id') and HandoffQueue(self.service.store).is_blocking(result['_case_id']):
                result.update(state='needs_review',should_send=False,handoff_reason='regla_contacto')
            return team.finish(result)
        except Exception:
            team.failed()
            raise

    def claim(self, reservation):
        team = self.reservation_team(reservation)
        team.claim_review()
        try:
            result = self.invoke(team, 'reservar_respuesta_correo', {'reservation': reservation})
            return team.finish({**result, 'state': 'sending'})
        except Exception:
            team.failed()
            raise

    def sent(self, reservation, gmail_id):
        team = self.reservation_team(reservation)
        with self.service.store.connect() as c:
            claimed = c.execute("UPDATE team_runs SET state='confirming' WHERE id=? AND state='sending'", (team.request_id,)).rowcount
        if claimed != 1:
            raise ValueError('La respuesta no espera confirmación Gmail')
        try:
            result = self.invoke(team, 'confirmar_envio_correo', {'reservation': reservation, 'gmail_id': gmail_id})
            return team.finish({**result, 'email_sent': True})
        except Exception:
            team.failed()
            raise
