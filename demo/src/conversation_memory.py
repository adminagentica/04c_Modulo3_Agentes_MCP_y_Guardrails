"""Memoria de turnos y acciones pendientes, separada por conversación del operador demo."""
import datetime as dt
import json
import re
import unicodedata
import uuid

ACTOR='ejecutivo-demo'
CONFIRMATIONS={'envialo','si envialo','si envia el recordatorio','confirmo el envio','apruebo el envio','confirmo enviar','enviar borrador','envia el borrador'}
CANCELLATIONS={'cancelalo','cancela el borrador','no lo envies','cancelar borrador','cancelar envio'}

def normalized(text):
    plain=''.join(c for c in unicodedata.normalize('NFD',text.lower()) if unicodedata.category(c)!='Mn')
    return re.sub(r'[^a-z0-9 ]','',plain).strip()

def now():return dt.datetime.now(dt.timezone.utc)

class ConversationMemory:
    def __init__(self,store):
        self.store=store
        with store.connect() as c:
            c.executescript('''
            CREATE TABLE IF NOT EXISTS chat_conversations(id TEXT PRIMARY KEY,actor TEXT,created TEXT,expires TEXT);
            CREATE TABLE IF NOT EXISTS chat_turns(id INTEGER PRIMARY KEY,conversation_id TEXT,request_id TEXT,role TEXT,content TEXT,metadata TEXT,created TEXT,
                UNIQUE(conversation_id,request_id,role));
            ''')
            if 'active_dni' not in {row[1] for row in c.execute('PRAGMA table_info(chat_conversations)')}:
                c.execute("ALTER TABLE chat_conversations ADD COLUMN active_dni TEXT NOT NULL DEFAULT ''")

    def ensure(self,ident=None,actor=ACTOR):
        if actor!=ACTOR:raise ValueError('Operador no autorizado')
        ident=ident or str(uuid.uuid4());uuid.UUID(ident)
        with self.store.connect() as c:
            row=c.execute('SELECT actor,expires FROM chat_conversations WHERE id=?',(ident,)).fetchone()
            if row and (row['actor']!=actor or row['expires']<=now().isoformat()):raise ValueError('Conversación no disponible para este operador')
            c.execute('INSERT OR IGNORE INTO chat_conversations(id,actor,created,expires) VALUES(?,?,?,?)',(ident,actor,now().isoformat(),(now()+dt.timedelta(days=30)).isoformat()))
        return ident

    def add(self,ident,request_id,role,content,metadata=None):
        self.ensure(ident);uuid.UUID(request_id)
        if not isinstance(content,str):raise ValueError('Texto de conversación inválido')
        if role not in {'user','assistant'}:raise ValueError('Rol de conversación inválido')
        with self.store.connect() as c:
            c.execute('INSERT INTO chat_turns(conversation_id,request_id,role,content,metadata,created) VALUES(?,?,?,?,?,?) ON CONFLICT(conversation_id,request_id,role) DO UPDATE SET content=excluded.content,metadata=excluded.metadata',
                      (ident,request_id,role,content[:16000],json.dumps(metadata or {}),now().isoformat()))

    def history(self,ident):
        self.ensure(ident)
        with self.store.connect() as c:
            rows=c.execute('SELECT request_id,role,content,metadata,created FROM chat_turns WHERE conversation_id=? ORDER BY id DESC LIMIT 20',(ident,)).fetchall()
        return [{**dict(row),'metadata':json.loads(row['metadata'])} for row in reversed(rows)]

    def require_confirmation(self,ident,request_id):
        self.ensure(ident)
        with self.store.connect() as c:
            row=c.execute("SELECT content FROM chat_turns WHERE conversation_id=? AND request_id=? AND role='user'",(ident,request_id)).fetchone()
        if not row or normalized(row['content']) not in CONFIRMATIONS:raise ValueError('No existe confirmación explícita del operador en este turno')

    def active_client(self,ident):
        self.ensure(ident)
        with self.store.connect() as c:
            return c.execute('SELECT active_dni FROM chat_conversations WHERE id=?',(ident,)).fetchone()[0]

    def select_client(self,ident,dni):
        """Contexto del ejecutivo; no sustituye la identidad del cliente por Gmail."""
        self.ensure(ident)
        if not re.fullmatch('[0-9]{8}',dni):raise ValueError('DNI inválido')
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            previous=c.execute('SELECT active_dni FROM chat_conversations WHERE id=?',(ident,)).fetchone()[0]
            if previous!=dni:
                # Migración: también invalida borradores anteriores a active_dni.
                if c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='reminder_drafts'").fetchone():
                    c.execute("UPDATE reminder_drafts SET state='superseded' WHERE conversation_id=? AND dni!=? AND state IN ('draft','approved')",(ident,dni))
                c.execute('UPDATE chat_conversations SET active_dni=? WHERE id=?',(dni,ident))
        return previous!=dni
