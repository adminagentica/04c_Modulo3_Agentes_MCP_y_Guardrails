"""Bandeja humana local: contexto mínimo, reclamo único y cierre sin reanudar acciones."""
import datetime as dt
import json
import uuid

REASONS = {
    'solicitud_explicita': 'El usuario solicita atención de un ejecutivo.',
    'evidencia_insuficiente': 'Falta evidencia documental suficiente o vigente.',
    'regla_contacto': 'Un control operativo impide continuar el contacto.',
    'fallo_validacion': 'El flujo se detuvo por una validación o un fallo técnico.',
    'envio_incierto': 'No se pudo confirmar el envío Gmail; revisar el buzón antes de volver a contactar.',
    'fallo_proveedor': 'El proveedor de generación no pudo completar la consulta.',
}
DECISIONS = {
    'revision_completada': 'Revisión completada; cualquier nueva acción requiere otra validación.',
    'solicitar_informacion': 'Se requiere información adicional del cliente o del ejecutivo.',
    'mantener_bloqueo': 'Se mantiene el bloqueo de acciones del caso.',
}
ACTOR = 'ejecutivo-demo'


def timestamp():
    return dt.datetime.now(dt.timezone.utc).isoformat()


class HandoffQueue:
    def __init__(self, store):
        self.store = store
        with store.connect() as c:
            c.executescript('''
            CREATE TABLE IF NOT EXISTS human_handoffs(
                id TEXT PRIMARY KEY,request_id TEXT UNIQUE,tenant TEXT,case_id TEXT,reason TEXT,
                status TEXT,assigned_to TEXT,decision TEXT,context TEXT,created TEXT,updated TEXT);
            CREATE TABLE IF NOT EXISTS human_handoff_events(
                id INTEGER PRIMARY KEY,handoff_id TEXT,actor TEXT,action TEXT,created TEXT);
            ''')

    def view(self, row):
        result = dict(row)
        result['context'] = json.loads(result['context'])
        result.update(reason_label=REASONS[result['reason']],
                      automation_paused=result['status'] != 'resolved' or result['decision'] == 'mantener_bloqueo',
                      resumed=False, email_sent=False)
        return result

    def create(self, request_id, reason, case_id=None, tenant='demo'):
        uuid.UUID(request_id)
        if tenant != 'demo' or reason not in REASONS:
            raise ValueError('Derivación fuera del ámbito o motivo inválido')
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            existing = c.execute('SELECT * FROM human_handoffs WHERE request_id=? AND tenant=?', (request_id, tenant)).fetchone()
            if existing:
                return self.view(existing)
            context = {'case_validated': bool(case_id), 'scope': 'synthetic_demo', 'actions_allowed': False}
            if case_id:
                case = self.store.case(tenant, case_id, c)
                context.update({k: case[k] for k in ('invoice', 'balance_cents', 'currency', 'due')})
                context['case_version'] = case['version']
            ident, now = str(uuid.uuid4()), timestamp()
            c.execute('INSERT INTO human_handoffs VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                      (ident, request_id, tenant, case_id, reason, 'pending', None, None, json.dumps(context), now, now))
            c.execute('INSERT INTO human_handoff_events(handoff_id,actor,action,created) VALUES(?,?,?,?)',
                      (ident, 'orquestador', 'created', now))
            if case_id:
                self.store.remember(c, tenant, case_id, request_id, 'agent_completed',
                                    {'agent_id': 'human_handoff', 'version': '1.0.0', 'status': 'pending', 'handoff_id': ident})
            return self.view(c.execute('SELECT * FROM human_handoffs WHERE id=?', (ident,)).fetchone())

    def list(self, tenant='demo'):
        if tenant != 'demo':
            raise ValueError('Ámbito no autorizado')
        with self.store.connect() as c:
            rows = c.execute("SELECT * FROM human_handoffs WHERE tenant=? ORDER BY CASE status WHEN 'pending' THEN 0 WHEN 'in_review' THEN 1 ELSE 2 END,created DESC LIMIT 100", (tenant,)).fetchall()
        return [self.view(row) for row in rows]

    def claim(self, ident, actor=ACTOR):
        if actor != ACTOR:
            raise ValueError('Ejecutivo no autorizado en esta demo')
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            changed = c.execute("UPDATE human_handoffs SET status='in_review',assigned_to=?,updated=? WHERE id=? AND tenant='demo' AND status='pending'", (actor, timestamp(), ident)).rowcount
            if changed != 1:
                raise ValueError('La derivación ya fue tomada o no está pendiente')
            c.execute('INSERT INTO human_handoff_events(handoff_id,actor,action,created) VALUES(?,?,?,?)', (ident, actor, 'claimed', timestamp()))
            return self.view(c.execute('SELECT * FROM human_handoffs WHERE id=?', (ident,)).fetchone())

    def resolve(self, ident, decision, actor=ACTOR):
        if actor != ACTOR or decision not in DECISIONS:
            raise ValueError('Decisión o ejecutivo no autorizado')
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            changed = c.execute("UPDATE human_handoffs SET status='resolved',decision=?,updated=? WHERE id=? AND tenant='demo' AND status='in_review' AND assigned_to=?", (decision, timestamp(), ident, actor)).rowcount
            if changed != 1:
                raise ValueError('Se debe tomar la derivación antes de resolverla; no repetir el cierre')
            row = c.execute('SELECT * FROM human_handoffs WHERE id=?', (ident,)).fetchone()
            c.execute('INSERT INTO human_handoff_events(handoff_id,actor,action,created) VALUES(?,?,?,?)', (ident, actor, decision, timestamp()))
            if row['case_id']:
                self.store.remember(c, row['tenant'], row['case_id'], row['request_id'], 'agent_completed',
                                    {'agent_id': 'human_reviewer', 'version': '1.0.0', 'status': 'resolved',
                                     'handoff_id': ident, 'decision': decision})
            return {**self.view(row), 'decision_label': DECISIONS[decision]}

    def is_blocking(self, case_id, tenant='demo'):
        with self.store.connect() as c:
            return bool(c.execute("SELECT 1 FROM human_handoffs WHERE tenant=? AND case_id=? AND (status IN ('pending','in_review') OR decision='mantener_bloqueo') LIMIT 1", (tenant, case_id)).fetchone())
