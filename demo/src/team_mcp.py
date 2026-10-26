"""Capacidades MCP internas acotadas a una consulta; sin herramientas de envío."""
import json
from datetime import timedelta
from mcp.server.fastmcp import FastMCP
from mcp.shared.memory import create_connected_server_and_client_session
from cobranza import fingerprint
from human_handoff import HandoffQueue


def create_team_tools(service, dni, retrieve, validate, channel="chat", handoff_scope=None, reminder_scope=None):
    server = FastMCP('Agentica herramientas del equipo')
    scope = {'case_id': None}
    if channel == 'reminder':
        from reminder_actions import ReminderActions
        if not reminder_scope or not reminder_scope.get('conversation_id'):raise ValueError('Falta conversación de la acción')
        actions=ReminderActions(service,validate)
        @server.tool()
        def preparar_recordatorio() -> dict:
            """Crea y devuelve un borrador inmutable para revisión; no envía."""
            return actions.create(reminder_scope['conversation_id'],reminder_scope['request_id'],reminder_scope['dni'],reminder_scope['rag'],reminder_scope.get('case_fingerprint'))
        @server.tool()
        def aprobar_recordatorio() -> dict:
            """Solo confirma si existe un turno auténtico del operador y un borrador mostrado."""
            return actions.approve(reminder_scope['conversation_id'],reminder_scope['request_id'],reminder_scope.get('dni',''),reminder_scope.get('draft_id'))
        @server.tool()
        def cancelar_recordatorio() -> dict:
            return actions.cancel(reminder_scope['conversation_id'])
        @server.tool()
        def reclamar_recordatorio() -> dict:
            """Reserva una única salida Gmail con aprobación y controles vigentes."""
            return actions.claim(reminder_scope['conversation_id'],reminder_scope['request_id'],reminder_scope['draft_id'])
        @server.tool()
        def registrar_recordatorio() -> dict:
            return actions.result(reminder_scope['conversation_id'],reminder_scope['request_id'],reminder_scope['draft_id'],reminder_scope.get('gmail_id'))
        return server
    if channel == 'handoff':
        if not handoff_scope or not handoff_scope.get('request_id'):
            raise ValueError('Falta el ámbito de la derivación humana')
        @server.tool()
        def derivar_a_humano(reason: str) -> dict:
            """Crea una derivación local; no notifica, resuelve ni envía correos."""
            return HandoffQueue(service.store).create(handoff_scope['request_id'],reason,handoff_scope.get('case_id'))
        return server
    if channel == 'mail':
        @server.tool()
        def preparar_consulta_correo(mensaje: dict) -> dict:
            """Valida identidad y prepara una respuesta; nunca ejecuta Gmail Send."""
            return service.prepare_email(mensaje)

        @server.tool()
        def reservar_respuesta_correo(reservation: str) -> dict:
            """Reserva una respuesta y revalida el caso antes del envío de n8n."""
            with service.store.connect() as c:
                row=c.execute('SELECT reply FROM email_inquiries WHERE reservation=?',(reservation,)).fetchone()
            if row:
                case_id=json.loads(row['reply']).get('_case_id')
                if case_id and HandoffQueue(service.store).is_blocking(case_id):
                    raise ValueError('La respuesta está detenida para revisión humana')
            return service.claim(reservation)

        @server.tool()
        def confirmar_envio_correo(reservation: str, gmail_id: str) -> dict:
            """Registra confirmación del proveedor; no envía ni acredita lectura."""
            return service.sent(reservation, gmail_id)
        return server
    if channel != 'chat':
        raise ValueError('Canal de herramientas desconocido')

    @server.tool()
    def saldo_cliente() -> dict:
        """Lee el cliente seleccionado; no permite sustituirlo mediante argumentos."""
        try:
            account = service.balance(dni)
        except ValueError:
            return {'matched': False}
        scope['case_id'] = account['case_id']
        return {'matched': True, 'account': account,
                'fingerprint': fingerprint(service.store.case('demo', account['case_id']))}

    @server.tool()
    def recordar_contexto() -> dict:
        """Recupera memoria filtrada del caso ya validado, nunca instrucciones libres."""
        if not scope['case_id']:
            raise ValueError('Se requiere validar el cliente antes de leer memoria')
        events = service.store.memory('demo', scope['case_id'])
        allowed_states = {'ok', 'answered', 'needs_review', 'clarify', 'blocked', 'error', 'failed', 'ready', 'prepared', 'sending', 'gmail_accepted', 'pending', 'in_review', 'resolved'}
        summary = []
        for event in events:
            payload = event['payload']
            summary.append({'event': event['event'], 'created': event['created'],
                            'status': payload.get('status') if payload.get('status') in allowed_states else None})
        return {'scope': 'validated_case', 'authority': 'context_only', 'events': summary}

    @server.tool()
    def evaluar_contacto() -> dict:
        """Reutiliza reglas de contacto; solo evalúa, no prepara ni envía mensajes."""
        if not scope['case_id']:
            raise ValueError('Se requiere validar el cliente antes de evaluar contacto')
        return service.reminder_eligibility(dni)

    @server.tool()
    def recuperar_politicas(pregunta: str) -> dict:
        """Recupera fragmentos autorizados del RAG; no genera permisos ni cifras."""
        if not 3 <= len(pregunta) <= 1500:
            raise ValueError('Pregunta documental inválida')
        return retrieve(pregunta)

    @server.tool()
    def verificar_contexto(expected_fingerprint: str, bundle: dict, check_contact: bool) -> dict:
        """Revalida fuentes, huella e historial antes de entregar una respuesta."""
        if bundle:
            validate(bundle)
        if expected_fingerprint:
            if not scope['case_id']:
                raise ValueError('Falta cliente validado')
            if fingerprint(service.store.case('demo', scope['case_id'])) != expected_fingerprint:
                raise ValueError('El caso cambió durante la consulta')
        return {'verified': True, 'reminder_check': service.reminder_eligibility(dni) if check_contact else None}

    return server


class TeamMcpSession:
    """Cliente SDK MCP con transporte en memoria, mismo protocolo y validación de herramientas."""
    def __init__(self, service, dni, retrieve, validate, channel="chat", handoff_scope=None, reminder_scope=None):
        self.server = create_team_tools(service, dni, retrieve, validate, channel, handoff_scope, reminder_scope)

    async def __aenter__(self):
        self.manager = create_connected_server_and_client_session(self.server, read_timeout_seconds=timedelta(seconds=180))
        self.session = await self.manager.__aenter__()
        return self

    async def __aexit__(self, *args):
        try:
            return await self.manager.__aexit__(*args)
        except ExceptionGroup as exc:
            raise ValueError('La sesión MCP se detuvo ante una validación o un fallo de herramienta') from exc

    async def call(self, name, arguments=None):
        result = await self.session.call_tool(name, arguments or {})
        if result.isError:
            # No trasladar mensajes internos, preguntas ni datos del proveedor al cliente.
            raise ValueError('La herramienta MCP no pudo validar la operación: ' + name)
        value = result.structuredContent
        if value is None:
            value = json.loads(''.join(x.text for x in result.content if x.type == 'text'))
        if not isinstance(value, dict):
            raise ValueError('Contrato de herramienta MCP inválido')
        return value
