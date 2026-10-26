"""Borrador inmutable, aprobación por turno y salida Gmail reservada una sola vez."""
import datetime as dt
from email.message import EmailMessage
import hashlib
import json
import re
import uuid
from cobranza import fingerprint,stamp
from conversation_memory import ConversationMemory,ACTOR
from customer_service import MAILBOX

class ReminderActions:
    def __init__(self,service,validate):
        self.service,self.validate=service,validate
        self.memory=ConversationMemory(service.store)
        with service.store.connect() as c:
            c.executescript('''
            CREATE TABLE IF NOT EXISTS reminder_drafts(id TEXT PRIMARY KEY,conversation_id TEXT,actor TEXT,case_id TEXT,dni TEXT,
                request_id TEXT,state TEXT,recipient TEXT,subject TEXT,body TEXT,digest TEXT,case_fingerprint TEXT,rag TEXT,created TEXT,expires TEXT,
                approval_request_id TEXT,approved_by TEXT,approved_at TEXT,gmail_id TEXT,outbox_key TEXT);
            CREATE UNIQUE INDEX IF NOT EXISTS reminder_draft_request ON reminder_drafts(request_id);
            ''')

    def view(self,row):
        return {key:row[key] for key in ('id','conversation_id','case_id','state','recipient','subject','body','created','expires','gmail_id')}

    def pending(self,conversation_id):
        self.memory.ensure(conversation_id)
        with self.service.store.connect() as c:
            row=c.execute('SELECT * FROM reminder_drafts WHERE conversation_id=? AND actor=? ORDER BY created DESC,rowid DESC LIMIT 1',(conversation_id,ACTOR)).fetchone()
        return dict(row) if row else None

    def create(self,conversation_id,request_id,dni,rag,expected_fingerprint=None):
        self.memory.ensure(conversation_id)
        if not rag or not rag.get('citations'):raise ValueError('No se puede preparar sin política verificada')
        self.validate(rag)
        with self.service.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            existing=c.execute('SELECT * FROM reminder_drafts WHERE request_id=? AND conversation_id=?',(request_id,conversation_id)).fetchone()
            if existing:return self.view(existing)
            active=c.execute('SELECT active_dni FROM chat_conversations WHERE id=?',(conversation_id,)).fetchone()
            if active and active[0] and active[0]!=dni:raise ValueError('Cambió el cliente activo antes de preparar el borrador')
            account=self.service.balance(dni,c);check=self.service.reminder_eligibility(dni,c)
            if not check['can_prepare'] or account['email']!=MAILBOX:raise ValueError('No se puede preparar el recordatorio de este cliente')
            case=self.service.store.case('demo',account['case_id'],c)
            if expected_fingerprint and fingerprint(case)!=expected_fingerprint:raise ValueError('Cambió el caso antes de crear el borrador')
            subject='Recordatorio de pago · DEMO Agentica'
            body=(f"Hola, {account['name']}:\n\nTe recordamos el saldo registrado de {account['currency']} {account['balance']} "
                  f"de la factura {account['invoice']}, con vencimiento {account['due']}. "
                  "Si ya realizaste el pago o consideras que existe una diferencia, solicita su revisión por el canal autorizado.\n\n"
                  "DEMO: datos sintéticos. No corresponde a una deuda real ni requiere efectuar un pago.\nEquipo Agentica")
            ident=str(uuid.uuid4());digest=hashlib.sha256(json.dumps([account['email'],subject,body],ensure_ascii=False).encode()).hexdigest()
            c.execute("UPDATE reminder_drafts SET state='superseded' WHERE conversation_id=? AND actor=? AND state='draft'",(conversation_id,ACTOR))
            c.execute('INSERT INTO reminder_drafts VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                      (ident,conversation_id,ACTOR,case['id'],dni,request_id,'draft',account['email'],subject,body,digest,fingerprint(case),json.dumps(rag),stamp(),(dt.datetime.now(dt.timezone.utc)+dt.timedelta(minutes=30)).isoformat(),None,None,None,None,None))
            self.service.store.remember(c,'demo',case['id'],request_id,'agent_completed',{'agent_id':'reminder_draft','version':'1.0.0','status':'draft','draft_id':ident})
            return self.view(c.execute('SELECT * FROM reminder_drafts WHERE id=?',(ident,)).fetchone())

    def cancel(self,conversation_id):
        draft=self.pending(conversation_id)
        if not draft or draft['state']!='draft':return {'state':'clarify','answer':'No hay un borrador pendiente que pueda cancelarse.','orchestrated_by':'n8n','citations':[]}
        with self.service.store.connect() as c:c.execute("UPDATE reminder_drafts SET state='cancelled' WHERE id=? AND state='draft'",(draft['id'],))
        return {'state':'answered','answer':'Borrador cancelado. No se envió ningún correo.','orchestrated_by':'n8n','citations':[]}

    def check(self,draft,c,ignore_key=''):
        active=c.execute('SELECT active_dni FROM chat_conversations WHERE id=?',(draft['conversation_id'],)).fetchone()
        if active and active[0] and active[0]!=draft['dni']:raise ValueError('Cambió el cliente activo; prepara otro borrador')
        account=self.service.balance(draft['dni'],c)
        case=self.service.store.case('demo',draft['case_id'],c)
        check=self.service.reminder_eligibility(draft['dni'],c,ignore_key=ignore_key)
        actual=hashlib.sha256(json.dumps([draft['recipient'],draft['subject'],draft['body']],ensure_ascii=False).encode()).hexdigest()
        if (draft['expires']<=stamp() or fingerprint(case)!=draft['case_fingerprint'] or actual!=draft['digest'] or
            account['case_id']!=draft['case_id'] or account['email']!=draft['recipient'] or draft['recipient']!=MAILBOX or not check['can_prepare']):
            raise ValueError('El borrador venció o cambiaron los datos, destinatario o controles; no se envió')
        return case

    def approve(self,conversation_id,request_id,selected_dni='',expected_draft_id=None):
        self.memory.require_confirmation(conversation_id,request_id)
        draft=self.pending(conversation_id)
        if not draft:return {'state':'clarify','answer':'Primero prepara y revisa un borrador en esta conversación. No se envió ningún correo.','citations':[],'orchestrated_by':'n8n'}
        if selected_dni and selected_dni!=draft['dni']:
            return {'state':'clarify','answer':'Cambió el cliente activo. Prepara y revisa un nuevo borrador para este cliente antes de confirmar.','citations':[],'orchestrated_by':'n8n'}
        if draft['state']=='draft' and expected_draft_id!=draft['id']:
            return {'state':'clarify','answer':'Falta identificar el borrador mostrado o ya existe otro más reciente. Revisa el último borrador antes de confirmar.','citations':[],'orchestrated_by':'n8n'}
        if draft['state']=='sent':return {'state':'answered','answer':'Este recordatorio ya fue enviado. No se volverá a enviar.','citations':[],'orchestrated_by':'n8n','draft':self.view(draft)}
        if draft['state']!='draft':return {'state':'processing' if draft['state'] in {'approved','sending'} else 'needs_review','answer':'El borrador ya fue procesado, cancelado o tiene un envío pendiente de confirmar. No se reintentará automáticamente; revisa Gmail y la ejecución.','citations':[],'orchestrated_by':'n8n'}
        try:
            self.validate(json.loads(draft['rag']))
            with self.service.store.connect() as c:
                c.execute('BEGIN IMMEDIATE');current=dict(c.execute('SELECT * FROM reminder_drafts WHERE id=?',(draft['id'],)).fetchone())
                if current['state']!='draft':return {'state':'processing','answer':'La confirmación ya fue procesada; no se repetirá el envío.','citations':[],'orchestrated_by':'n8n'}
                self.check(current,c)
                with_seen=c.execute("SELECT metadata FROM chat_turns WHERE conversation_id=? AND request_id=? AND role='assistant'",(conversation_id,current['request_id'])).fetchone()
                if not with_seen or json.loads(with_seen['metadata']).get('draft',{}).get('id')!=draft['id']:raise ValueError('Falta el turno en que se mostró el borrador')
                c.execute("UPDATE reminder_drafts SET state='approved',approval_request_id=?,approved_by=?,approved_at=? WHERE id=? AND state='draft'",(request_id,ACTOR,stamp(),draft['id']))
                self.service.store.remember(c,'demo',draft['case_id'],request_id,'agent_completed',{'agent_id':'operator_confirmation','version':'1.0.0','status':'approved','draft_id':draft['id']})
        except Exception:
            with self.service.store.connect() as c:c.execute("UPDATE reminder_drafts SET state='blocked' WHERE id=? AND state='draft'",(draft['id'],))
            return {'state':'needs_review','answer':'No se envió el recordatorio: venció el borrador o cambió el caso, la política o un control. Debe revisarse y prepararse de nuevo.','citations':[],'orchestrated_by':'n8n'}
        return {'state':'ready_to_send','answer':'Confirmación registrada. n8n procesará el envío aprobado.','dispatch_requested':True,'draft_id':draft['id'],'conversation_id':conversation_id,'confirmation_request_id':request_id,'citations':[],'orchestrated_by':'n8n'}

    def claim(self,conversation_id,request_id,draft_id):
        self.memory.ensure(conversation_id)
        with self.service.store.connect() as c:
            row=c.execute('SELECT * FROM reminder_drafts WHERE id=? AND conversation_id=? AND actor=?',(draft_id,conversation_id,ACTOR)).fetchone()
        if not row:raise ValueError('Borrador fuera del ámbito')
        self.validate(json.loads(row['rag']))
        self.memory.require_confirmation(conversation_id,request_id)
        with self.service.store.connect() as c:
            c.execute('BEGIN IMMEDIATE');draft=dict(c.execute('SELECT * FROM reminder_drafts WHERE id=?',(draft_id,)).fetchone())
            if draft['state']!='approved' or draft['approval_request_id']!=request_id or draft['approved_by']!=ACTOR:raise ValueError('Falta aprobación vigente o el envío ya fue reservado')
            case=self.check(draft,c);key=self.service.store.idempotency_key(case)
            message=EmailMessage();message['To']=draft['recipient'];message['Subject']=draft['subject'];message.set_content(draft['body']);mime=message.as_string()
            c.execute('INSERT INTO outbox VALUES(?,?,?,?,?,?,?,?,?)',(key,'demo',case['id'],request_id,case['version'],'gmail_sending',stamp(),mime,hashlib.sha256(mime.encode()).hexdigest()))
            c.execute("UPDATE reminder_drafts SET state='sending',outbox_key=? WHERE id=?",(key,draft_id))
        return {'draft_id':draft_id,'conversation_id':conversation_id,'confirmation_request_id':request_id,'to':draft['recipient'],'subject':draft['subject'],'body':draft['body']}

    def result(self,conversation_id,request_id,draft_id,gmail_id):
        accepted=isinstance(gmail_id,str) and bool(re.fullmatch(r'[a-fA-F0-9]{8,64}',gmail_id))
        with self.service.store.connect() as c:
            c.execute('BEGIN IMMEDIATE');row=c.execute('SELECT * FROM reminder_drafts WHERE id=? AND conversation_id=? AND actor=?',(draft_id,conversation_id,ACTOR)).fetchone()
            if not row or row['state']!='sending' or row['approval_request_id']!=request_id:raise ValueError('El recordatorio no espera confirmación de envío')
            c.execute('UPDATE reminder_drafts SET state=?,gmail_id=? WHERE id=?',('sent' if accepted else 'unknown',gmail_id if accepted else None,draft_id))
            c.execute('UPDATE outbox SET state=? WHERE key=?',('gmail_accepted' if accepted else 'unknown',row['outbox_key']))
            self.service.store.remember(c,'demo',row['case_id'],request_id,'agent_completed',{'agent_id':'reminder_gmail','version':'1.0.0','status':'gmail_accepted' if accepted else 'unknown','draft_id':draft_id,'gmail_id':gmail_id if accepted else None})
        return {'state':'answered' if accepted else 'needs_review','route':'reminder_send','answer':('Recordatorio enviado a '+row['recipient']+'. Gmail aceptó el mensaje con ID '+gmail_id+'.' if accepted else 'No se pudo confirmar el envío. No se reintentará automáticamente; revisa Gmail y la ejecución antes de continuar.'),
                'citations':[],'email_sent':accepted,'gmail_id':gmail_id if accepted else None,'draft_id':draft_id,'conversation_id':conversation_id,'request_id':request_id,'orchestrated_by':'n8n','model':'no-invocado',**({'handoff_reason':'envio_incierto'} if not accepted else {})}
