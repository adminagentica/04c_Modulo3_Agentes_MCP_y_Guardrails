"""App local de ejecutivo, API n8n y MCP Python; no envía correos por su cuenta."""
import asyncio
from contextlib import asynccontextmanager
import hmac
import json
import os
import re
from pathlib import Path
import secrets
import time
import uuid
from starlette.applications import Starlette
from starlette.responses import JSONResponse, FileResponse
from starlette.routing import Route, Mount
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
import uvicorn
from customer_service import CustomerService
from mail_orchestration import MailOrchestrator
from human_handoff import HandoffQueue
from conversation_memory import ConversationMemory
from reminder_actions import ReminderActions
from reminder_orchestration import ReminderOrchestrator
from rag_client import validate_bundle
from mcp_server import create_mcp
from web_orchestration import ChatOrchestrator, ask_n8n, N8nUnavailable, MODEL, WORKFLOW

ROOT = Path(__file__).resolve().parents[1]


def build_app(service=None, admin_token=None):
    service = service or CustomerService()
    service.store.seed()
    service.seed()
    token = admin_token or os.getenv('COBRANZA_TOKEN', '')
    if len(token) < 24:
        raise ValueError('COBRANZA_TOKEN debe contener al menos 24 caracteres')
    mcp = create_mcp(service)
    chat = ChatOrchestrator(service)
    mail = MailOrchestrator(service)
    handoffs = HandoffQueue(service.store)
    conversations = ConversationMemory(service.store)
    reminders = ReminderOrchestrator(service)
    mcp_app = mcp.streamable_http_app()
    sessions, attempts = {}, {}

    class Access(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            origin = request.headers.get('origin')
            if origin and origin not in {'http://127.0.0.1:8790', 'http://localhost:8790'}:
                return JSONResponse({'error': 'Origen no autorizado'}, status_code=403)
            if request.url.path in {'/', '/app.js', '/style.css', '/login'}:
                return await call_next(request)
            is_admin = hmac.compare_digest(request.headers.get('authorization', ''), 'Bearer '+token)
            is_web = sessions.get(request.cookies.get('agentica_session', ''), 0) > time.time()
            if not is_admin and (not is_web or request.url.path.startswith(('/mail/', '/reminder/', '/mcp', '/legacy/', '/chat/'))):
                return JSONResponse({'error': 'Acceso requerido'}, status_code=401)
            return await call_next(request)

    def conversation_id(request):
        cookie=request.cookies.get('agentica_conversation','')
        parts=cookie.split('.')
        if len(parts)==2:
            ident,signature=parts
            expected=hmac.new(token.encode(),ident.encode(),'sha256').hexdigest()
            if hmac.compare_digest(signature,expected):
                try:return conversations.ensure(ident)
                except ValueError:pass
        return conversations.ensure()

    def conversation_cookie(response,ident):
        signature=hmac.new(token.encode(),ident.encode(),'sha256').hexdigest()
        response.set_cookie('agentica_conversation',ident+'.'+signature,httponly=True,samesite='strict',max_age=30*86400)

    async def body(request):
        raw = await request.body()
        if len(raw) > 250000:
            raise ValueError('Solicitud demasiado grande')
        return json.loads(raw)

    async def index(_):
        return FileResponse(ROOT/'web/index.html', headers={'Cache-Control':'no-store'})

    async def asset(request):
        return FileResponse(ROOT/'web'/request.path_params['asset'])

    async def login(request):
        data = await body(request)
        host = request.client.host if request.client else 'local'
        recent = [x for x in attempts.get(host, []) if x > time.time()-60]
        attempts[host] = recent
        if len(recent) >= 5:
            return JSONResponse({'error':'Espera un minuto antes de intentar de nuevo.'}, status_code=429)
        password = os.getenv('EXECUTIVE_DEMO_PASSWORD', 'DemoAgentica!2026')
        if not hmac.compare_digest(str(data.get('password', '')), password):
            recent.append(time.time())
            return JSONResponse({'error':'Clave incorrecta'}, status_code=401)
        session = secrets.token_urlsafe(32)
        sessions[session] = time.time()+8*3600
        response = JSONResponse({'ok':True, 'profile':'ejecutivo-demo'})
        response.set_cookie('agentica_session',session,httponly=True,samesite='strict',max_age=8*3600)
        conversation_cookie(response,conversation_id(request))
        return response

    async def api(request):
        try:
            data = await body(request) if request.method == 'POST' else {}
            active_conversation=None
            if request.url.path == '/api/ask':
                question=data['question'];dni=str(data.get('dni',''))
                if not isinstance(question,str) or not 3<=len(question.strip())<=1000 or (dni and not re.fullmatch('[0-9]{8}',dni)):
                    raise ValueError('Pregunta o DNI inválidos')
                active_conversation=conversation_id(request)
                result = await asyncio.to_thread(ask_n8n,question,dni,token,active_conversation,data['draft_id']) if data.get('draft_id') else await asyncio.to_thread(ask_n8n,question,dni,token,active_conversation)
            elif request.url.path == '/api/conversation':
                active_conversation=conversation_id(request)
                draft=await asyncio.to_thread(ReminderActions(service,validate_bundle).pending,active_conversation)
                result={'conversation_id':active_conversation,'turns':await asyncio.to_thread(conversations.history,active_conversation),
                        'selected_dni':conversations.active_client(active_conversation),
                        'pending_draft':ReminderActions(service,validate_bundle).view(draft) if draft else None}
            elif request.url.path == '/api/handoffs':
                result = {'handoffs':await asyncio.to_thread(handoffs.list)}
            elif request.url.path == '/api/handoffs/claim':
                result = await asyncio.to_thread(handoffs.claim,data['id'])
            elif request.url.path == '/api/handoffs/resolve':
                result = await asyncio.to_thread(handoffs.resolve,data['id'],data['decision'])
            elif request.url.path == '/api/status':
                from rag_client import request as rag_request
                try:
                    rag = await asyncio.to_thread(rag_request, '/api/rag/status')
                    rag_state = rag.get('state', 'unknown')
                except Exception:
                    rag_state = 'unavailable'
                with service.store.connect() as c:
                    gmail_verified = bool(c.execute("SELECT 1 FROM email_inquiries WHERE state='gmail_accepted' LIMIT 1").fetchone())
                result = {'version':'0.8.1','mcp':'Python SDK / Streamable HTTP','mailbox':'contacto@agentica.com.pe',
                          'data':'synthetic','gmail':'Respuesta verificada' if gmail_verified else 'Pendiente de prueba OAuth en n8n',
                          'gmail_verified':gmail_verified,'dni_demo':'74851236', 'rag_state':rag_state,
                          'chat_transport':'n8n_webhook','chat_model':MODEL,'chat_workflow':WORKFLOW}
            elif request.url.path == '/chat/context':
                result = await asyncio.to_thread(chat.prepare,data['question'],str(data.get('dni','')),data['request_id'],data.get('conversation_id'),data.get('draft_id'))
            elif request.url.path == '/chat/result':
                result = await asyncio.to_thread(chat.complete,data['request_id'],data['openai_response'],data['openai_status'],str(data['execution_id']))
            elif request.url.path == '/reminder/claim':
                result = await asyncio.to_thread(reminders.claim,data['conversation_id'],data['confirmation_request_id'],data['draft_id'])
            elif request.url.path == '/reminder/result':
                result = await asyncio.to_thread(reminders.result,data['conversation_id'],data['confirmation_request_id'],data['draft_id'],data.get('gmail_id'),str(data['execution_id']))
            elif request.url.path == '/mail/prepare':
                result = await asyncio.to_thread(mail.prepare, data)
            elif request.url.path == '/mail/claim':
                result = await asyncio.to_thread(mail.claim, data['reservation'])
            elif request.url.path == '/mail/sent':
                result = await asyncio.to_thread(mail.sent, data['reservation'], data['gmail_id'])
            elif request.url.path == '/legacy/start':
                result = await asyncio.to_thread(service.store.start, data['tenant_id'], data['case_id'], 'n8n', data.get('mode','demo'))
            elif request.url.path == '/legacy/agent':
                result = await asyncio.to_thread(service.store.agent, data['trace_id'], data['agent_id'])
            elif request.url.path == '/legacy/rag':
                result = await asyncio.to_thread(service.store.rag_context, data['trace_id'])
            elif request.url.path == '/legacy/finish':
                result = await asyncio.to_thread(service.store.finish, data['trace_id'])
            else:
                raise ValueError('Ruta desconocida')
            response=JSONResponse(result)
            if active_conversation:conversation_cookie(response,active_conversation)
            return response
        except N8nUnavailable as exc:
            return JSONResponse({'error':str(exc)},status_code=503)
        except (ValueError, KeyError):
            return JSONResponse({'error':'No se pudo validar la solicitud o la evidencia. No se realizaron envíos.'}, status_code=400)
        except Exception:
            return JSONResponse({'error':'Servicio de datos o RAG no disponible. Solicita revisión.'}, status_code=503)

    @asynccontextmanager
    async def lifespan(app):
        async with mcp.session_manager.run():
            yield

    routes = [Route('/',index),Route('/login',login,methods=['POST'])]
    async def js(_): return FileResponse(ROOT/'web/app.js')
    async def css(_): return FileResponse(ROOT/'web/style.css')
    routes += [Route('/app.js',js),Route('/style.css',css),Route('/api/status',api),Route('/api/conversation',api),Route('/api/ask',api,methods=['POST']),Route('/api/handoffs',api),Route('/api/handoffs/claim',api,methods=['POST']),Route('/api/handoffs/resolve',api,methods=['POST'])]
    routes += [Route(p,api,methods=['POST']) for p in ['/mail/prepare','/mail/claim','/mail/sent','/reminder/claim','/reminder/result']]
    routes += [Route('/legacy/'+p,api,methods=['POST']) for p in ['start','agent','rag','finish']]
    routes += [Route('/chat/'+p,api,methods=['POST']) for p in ['context','result']]
    routes += [Mount('/',mcp_app)]
    app = Starlette(routes=routes,lifespan=lifespan)
    app.add_middleware(Access)
    app.add_middleware(TrustedHostMiddleware,allowed_hosts=['127.0.0.1','localhost','testserver'])
    return app


if __name__ == '__main__':
    uvicorn.run(build_app(), host='127.0.0.1', port=8790, access_log=False)
