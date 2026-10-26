"""Consultas de cliente por correo y asistente local del ejecutivo, con datos sintéticos."""
import datetime as dt
from pathlib import Path
from email.utils import getaddresses
import hashlib
import json
import re
import secrets
import unicodedata
from cobranza import Store, stamp, fingerprint
from rag_client import CONFIG as RAG_CONFIG, request as rag_request, validate_bundle

MAILBOX = 'contacto@agentica.com.pe'
SUBJECT_PREFIX = 'AGENTICA-PRUEBA Consulta deuda'


def email_address(value):
    if not isinstance(value, str) or '\r' in value or '\n' in value:
        raise ValueError('Correo inválido')
    addresses = getaddresses([value])
    if len(addresses) != 1:
        raise ValueError('Debe existir un solo remitente')
    address = addresses[0][1].strip().lower()
    if not re.fullmatch(r'[A-Za-z0-9.!#$%&\'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', address):
        raise ValueError('Formato de correo inválido')
    return address


def normalize_gmail(message):
    """Acepta el formato full del conector o raw parseado por Gmail Trigger de n8n."""
    payload = message.get('payload', {})
    headers = message.get('headers') or payload.get('headers') or {}
    if isinstance(headers, list):
        headers = {h['name'].lower(): h['value'] for h in headers}
    else:
        headers = {k.lower(): v for k, v in headers.items()}
    def header(name):
        text = headers.get(name, '')
        return re.sub(r'^' + re.escape(name) + r':\s*', '', str(text), flags=re.I)
    sender = message.get('from')
    if isinstance(sender, dict):
        values = sender.get('value', [])
        if len(values) != 1:
            raise ValueError('Remitente ambiguo')
        sender = values[0].get('address', '')
    sender = sender or header('from')
    def plain(part):
        if part.get('mime_type', '').lower() == 'text/plain':
            return part.get('body', {}).get('content') or ''
        return '\n'.join(plain(x) for x in part.get('parts', []))
    body = message.get('text') or plain(payload)
    if not body and payload.get('mime_type') == 'text/html':
        body = re.sub('<[^>]+>', ' ', payload.get('body', {}).get('content') or '')
    return {'message_id': message.get('id', ''), 'sender': email_address(sender),
            'subject': message.get('subject') or header('subject'), 'text': body[:20000],
            'labels': message.get('labelIds', message.get('label_ids', [])),
            'in_reply_to': header('in-reply-to'), 'authentication_results': header('authentication-results'),
            'auto_submitted': header('auto-submitted')}


class CustomerService:
    def __init__(self, store=None):
        self.store = store or Store()
        with self.store.connect() as c:
            c.executescript('''
            CREATE TABLE IF NOT EXISTS inquiry_customers(dni TEXT PRIMARY KEY, email TEXT NOT NULL, case_id TEXT NOT NULL, name TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS email_inquiries(message_id TEXT PRIMARY KEY, sender TEXT, state TEXT, reservation TEXT UNIQUE, reply TEXT, reply_digest TEXT, gmail_id TEXT, created TEXT);
            CREATE TABLE IF NOT EXISTS inquiry_contact_controls(case_id TEXT PRIMARY KEY,payment_history_checked INTEGER,promises_checked INTEGER,pending_payment INTEGER,broken_promise INTEGER,special_attention INTEGER,authorized_channel TEXT);
            CREATE TABLE IF NOT EXISTS executive_questions(id INTEGER PRIMARY KEY, question TEXT, route TEXT, case_id TEXT, citations TEXT, created TEXT);
            ''')

    def seed(self):
        """No altera la cartera de la versión previa ni importa clientes del RAG."""
        with self.store.connect() as c:
            fixtures=json.loads((Path(__file__).resolve().parents[1]/'config/demo-customers.json').read_text())
            for fixture in fixtures:
                dni,case_id,amount,name=(fixture[k] for k in ('dni','case_id','amount_cents','name'))
                c.execute('INSERT OR IGNORE INTO inquiry_customers VALUES(?,?,?,?)', (dni, MAILBOX, case_id, name))
                due = (dt.datetime.now(dt.timezone.utc).date() - dt.timedelta(days=fixture['overdue_days'])).isoformat()
                c.execute('INSERT OR IGNORE INTO cases VALUES(?,?,?,?,?,?,?,?,?,?,?)', ('demo', case_id, 'F-'+case_id, 1, amount, 'PEN', due, MAILBOX, 1, 0, 0))
                c.execute('INSERT OR IGNORE INTO inquiry_contact_controls VALUES(?,?,?,?,?,?,?)',
                          (case_id,1,1,int(fixture['pending_payment']),0,0,'EMAIL'))

    def balance(self, dni):
        if not isinstance(dni, str) or not re.fullmatch(r'\d{8}', dni):
            raise ValueError('DNI debe contener exactamente 8 dígitos')
        with self.store.connect() as c:
            row = c.execute('SELECT * FROM inquiry_customers WHERE dni=?', (dni,)).fetchone()
        if not row:
            raise ValueError('No se pudo validar la identidad')
        case = self.store.case('demo', row['case_id'])
        return {'case_id': case['id'], 'name': row['name'], 'email': row['email'], 'dni_masked': '******'+dni[-2:],
                'balance_cents': case['balance_cents'], 'balance': f"{case['balance_cents']/100:.2f}",
                'currency': case['currency'], 'invoice': case['invoice'], 'due': case['due'],
                'source': 'SQLite: cases (datos sintéticos)', 'version': case['version']}

    def reminder_eligibility(self,dni):
        """Evalúa una preparación de prueba; no autoriza ni ejecuta un envío."""
        account=self.balance(dni)
        case=self.store.case('demo',account['case_id'])
        rules=self.store.rules(case)
        reasons=list(rules['reasons'])
        # El motor de envío original mantiene su restricción example.test.
        # Solo la vista previa del cliente sintético puede usar la cuenta de prueba autorizada.
        self_test=(case['id'].startswith('MAIL-DEMO-') and account['email']==MAILBOX and case['recipient']==MAILBOX)
        if self_test:
            reasons=[x for x in reasons if x!='destinatario_fuera_entorno_demo']
        if case['recipient']!=account['email']:
            reasons.append('correo_no_coincide_con_registro')
        days_overdue=(dt.datetime.now(dt.timezone.utc).date()-dt.date.fromisoformat(case['due'])).days
        with self.store.connect() as c:
            control=c.execute('SELECT * FROM inquiry_contact_controls WHERE case_id=?',(case['id'],)).fetchone()
        if not control or not control['payment_history_checked'] or not control['promises_checked']:
            reasons.append('historial_no_verificado')
        if control:
            for key,reason in [('pending_payment','pago_pendiente_conciliacion'),('broken_promise','promesa_incumplida'),('special_attention','atencion_especial')]:
                if control[key]:reasons.append(reason)
            if control['authorized_channel']!='EMAIL':reasons.append('canal_no_autorizado')
        if days_overdue>30:reasons.append('fuera_gestion_temprana')
        return {'can_prepare':not reasons,'blocking_reasons':reasons,'recipient':account['email'],
                'scope':'synthetic_preview_only','requires_explicit_confirmation':True,'sent':False,
                'days_overdue':days_overdue,'controls_verified':bool(control and control['payment_history_checked'] and control['promises_checked']),
                'policy_version':rules['policy_version'],'evaluated_at':rules['evaluated_at']}

    def prepare_email(self, message):
        incoming = normalize_gmail(message)
        ident = incoming['message_id']
        if not re.fullmatch(r'[a-fA-F0-9]{8,64}', ident):
            raise ValueError('Se requiere ID de mensaje Gmail auténtico')
        subject = incoming['subject']
        if not subject.startswith(SUBJECT_PREFIX) or incoming['in_reply_to'] or incoming['auto_submitted']:
            return {'state': 'ignored', 'should_send': False, 'reason': 'fuera_del_recorrido_o_respuesta_automatica'}
        # Esta iteración solo autoriza la cuenta de prueba indicada por el usuario.
        self_test = incoming['sender'] == MAILBOX and {'SENT', 'INBOX'}.issubset(set(incoming['labels']))
        if not self_test:
            return {'state': 'rejected', 'should_send': False, 'reason': 'remitente_no_autorizado_en_prueba'}
        with self.store.connect() as c:
            if c.execute('SELECT 1 FROM email_inquiries WHERE message_id=?', (ident,)).fetchone():
                return {'state': 'duplicate', 'should_send': False}
        dnis = set(re.findall(r'\bDNI(?:\s+es)?\s*[:#-]?\s*(\d{8})\b', incoming['text'], flags=re.I))
        valid = False
        account_snapshot = None
        try:
            if len(dnis) != 1:
                raise ValueError('DNI ausente o ambiguo')
            account = self.balance(next(iter(dnis)))
            if account['email'].lower() != incoming['sender']:
                raise ValueError('Correo y DNI no coinciden')
            valid = True
            account_snapshot = fingerprint(self.store.case('demo', account['case_id']))
            text = (f"Hola, {account['name']}:\n\nValidamos la coincidencia de tu correo y DNI {account['dni_masked']} "
                    f"con el registro de prueba.\nSaldo registrado: {account['currency']} {account['balance']}.\n"
                    f"Factura: {account['invoice']}.\nVencimiento: {account['due']}.\n\n"
                    "Si registras un pago pendiente de aplicación, solicita su revisión.\n"
                    "DEMO: datos sintéticos; no corresponde a una deuda real ni requiere pago.\nEquipo de Agentica")
        except ValueError:
            text = ('No pudimos validar la coincidencia de correo y DNI. No se muestran datos de deuda. '
                    'Solicita revisión al ejecutivo de cobranza.\nDEMO de Agentica, sin datos reales.')
        reservation = secrets.token_urlsafe(24)
        reply = {'to': MAILBOX, 'subject': 'Respuesta de deuda · DEMO Agentica', 'body': text}
        if valid:
            reply['_case_id'] = account['case_id']
            reply['_case_fingerprint'] = account_snapshot
        digest = hashlib.sha256(json.dumps(reply, sort_keys=True).encode()).hexdigest()
        with self.store.connect() as c:
            inserted = c.execute('INSERT OR IGNORE INTO email_inquiries VALUES(?,?,?,?,?,?,?,?)',
                                 (ident, incoming['sender'], 'prepared', reservation, json.dumps(reply), digest, None, stamp())).rowcount
            if not inserted:
                return {'state': 'duplicate', 'should_send': False}
            if valid:
                self.store.remember(c,'demo',account['case_id'],'gmail:'+ident,'agent_completed',
                                    {'agent_id':'identity_guard','version':'1.0.0','status':'email_dni_matched',
                                     'case_version':account['version']})
        return {'state': 'prepared', 'should_send': True, 'identity_validated': valid,
                'reservation': reservation, 'message_id': ident, 'reply_digest': digest, **reply}

    def claim(self, reservation):
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            row = c.execute('SELECT * FROM email_inquiries WHERE reservation=?', (reservation,)).fetchone()
            if not row or row['state'] != 'prepared':
                raise ValueError('Envío ya reclamado o desconocido; no reintentar')
            reply = json.loads(row['reply'])
            if '_case_id' in reply and fingerprint(self.store.case('demo',reply['_case_id'],c)) != reply['_case_fingerprint']:
                raise ValueError('Cambió la cartera desde la consulta; no se envió información obsoleta')
            c.execute("UPDATE email_inquiries SET state='sending' WHERE reservation=?", (reservation,))
        return {'reservation': reservation, 'message_id': row['message_id'], 'reply_digest': row['reply_digest'], **json.loads(row['reply'])}

    def sent(self, reservation, gmail_id):
        if not re.fullmatch(r'[a-fA-F0-9]{8,64}', gmail_id):
            raise ValueError('Confirmación Gmail inválida')
        with self.store.connect() as c:
            row=c.execute('SELECT message_id,reply FROM email_inquiries WHERE reservation=?',(reservation,)).fetchone()
            changed = c.execute("UPDATE email_inquiries SET state='gmail_accepted',gmail_id=? WHERE reservation=? AND state='sending'", (gmail_id, reservation)).rowcount
            if not changed:
                raise ValueError('Estado de envío inválido')
            reply=json.loads(row['reply'])
            if '_case_id' in reply:
                self.store.remember(c,'demo',reply['_case_id'],'gmail:'+row['message_id'],'agent_completed',
                                    {'agent_id':'gmail_dispatch','version':'1.0.0','status':'gmail_accepted','gmail_message_id':gmail_id})
        return {'state': 'gmail_accepted', 'gmail_message_id': gmail_id}

    def policies(self, question):
        if not isinstance(question, str) or not 4 <= len(question.strip()) <= 1000:
            raise ValueError('Pregunta debe contener de 4 a 1000 caracteres')
        status = rag_request('/api/rag/status')
        result = rag_request('/api/rag/query', {'question': question, 'actor': 'asesor'})
        if result.get('insufficientEvidence') is not False:
            return {'route': 'rag', 'state': 'escalate', 'answer': 'No hay evidencia suficiente. Solicita revisión.', 'citations': []}
        bundle = {'index_version': status['indexVersion'], 'citations': result['citations']}
        validate_bundle(bundle)
        answer = result.get('answer','').strip()
        cited_ids = {str(x['id']) for x in result['citations']}
        inline_ids = set(re.findall(r'\[(\d+)\]',answer))
        if answer.rstrip(' ?¿.') == question.strip().rstrip(' ?¿.') or not inline_ids or not inline_ids.issubset(cited_ids):
            excerpts = '\n\n'.join(f"[{x['id']}] {x['code']} {x['version']} · {x['section']}\n{x['content'][:450]}" for x in result['citations'])
            return {'route':'rag','state':'needs_review','answer':'El modelo no produjo una respuesta verificable. Estos son los pasajes recuperados para revisión del ejecutivo:\n\n'+excerpts,
                    'citations':result['citations'],'index_version':status['indexVersion'],'method':'extractive_review_required'}
        return {'route': 'rag', 'state': 'answered', 'answer': result['answer'],
                'citations': result['citations'], 'index_version': status['indexVersion'], 'model': result.get('generation', {}).get('model')}

    def ask(self, question, dni=''):
        if not isinstance(question, str) or not 3 <= len(question.strip()) <= 1000:
            raise ValueError('Ingresa una pregunta de 3 a 1000 caracteres')
        normalized = ''.join(x for x in unicodedata.normalize('NFD', question.lower()) if unicodedata.category(x) != 'Mn')
        found = re.findall(r'\b\d{8}\b', question)
        if len(set(found)) > 1 or (dni and found and set(found) != {dni}):
            return {'route':'clarify','state':'clarify','answer':'La pregunta y el cliente seleccionado no identifican un único DNI. Revisa el contexto antes de consultar.','citations':[]}
        if not dni and len(set(found)) == 1:
            dni = found[0]
        policy_intent = any(x in normalized for x in ('politica', 'manual', 'promesa', 'concili', 'condicion', 'norma', 'regla', 'control', 'pol-', 'man-'))
        account_intent = any(x in normalized for x in ('saldo', 'deuda', 'factura', 'vencimiento', 'debo'))
        if policy_intent:
            result = self.policies(question)
            if account_intent and dni:
                account = self.balance(dni)
                result = {**result,'route':'account+rag','account':account,
                          'answer':f"Saldo registrado: {account['currency']} {account['balance']} (DNI {account['dni_masked']}).\n\nPolíticas:\n"+result['answer']}
        elif account_intent:
            if not dni:
                return {'route': 'account', 'state': 'needs_dni', 'answer': 'Indica el DNI sintético para consultar el saldo.', 'citations': []}
            account = self.balance(dni)
            result = {'route': 'account', 'state': 'answered', 'answer': f"{account['name']} · DNI {account['dni_masked']}\nSaldo: {account['currency']} {account['balance']}\nFactura: {account['invoice']}\nVencimiento: {account['due']}",
                      'account': account, 'citations': [], 'source': account['source']}
        else:
            result = {'route': 'clarify', 'state': 'clarify', 'answer': 'Puedo consultar saldos, facturas y políticas. Indica qué necesitas.', 'citations': []}
        with self.store.connect() as c:
            c.execute('INSERT INTO executive_questions(question,route,case_id,citations,created) VALUES(?,?,?,?,?)',
                      (question, result['route'], result.get('account', {}).get('case_id'), json.dumps([{'code':x['code'],'version':x['version'],'section':x['section']} for x in result['citations']]), stamp()))
        return result
