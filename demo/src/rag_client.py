"""Adapter de solo lectura para el RAG existente, sin copiar sus modelos ni corpus."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import urllib.parse
import urllib.request

CONFIG = json.loads((Path(__file__).resolve().parents[1] / 'config/rag-agent.json').read_text())


def request(path, body=None):
    base = os.getenv('COBRANZA_RAG_URL', CONFIG['base_url']).rstrip('/')
    url = urllib.parse.urlsplit(base)
    if url.scheme != 'http' or url.hostname not in {'127.0.0.1', 'localhost'} or url.path or url.query or url.fragment or url.username:
        raise ValueError('RAG debe ser un servicio local sin redirecciones')
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args):
            raise ValueError('Redirección RAG rechazada')
    req = urllib.request.Request(base + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect()).open(req, timeout=CONFIG['timeout_seconds']) as r:
        raw = r.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError('Respuesta RAG demasiado grande')
        return json.loads(raw)


def source_fingerprint():
    configured = Path(os.getenv('COBRANZA_RAG_CORPUS', CONFIG['corpus_dir'])).expanduser()
    corpus = (configured if configured.is_absolute() else Path(__file__).resolve().parents[1] / configured).resolve()
    manifest_bytes = (corpus / 'lineage_manifest.json').read_bytes()
    manifest = json.loads(manifest_bytes)
    files = []
    for doc in manifest['documents']:
        if not re.fullmatch(r'[A-Z]+-[A-Z]+-\d+', doc['code']) or not re.fullmatch(r'v\d+', doc['version']):
            raise ValueError('Identificador de fuente inválido')
        filename = doc['code'] + '_' + doc['version'] + '.docx'
        file = (corpus / filename).resolve()
        if file.parent != corpus:
            raise ValueError('Fuente fuera del corpus')
        files.append([filename, hashlib.sha256(file.read_bytes()).hexdigest()])
    canonical = json.dumps({'manifest': hashlib.sha256(manifest_bytes).hexdigest(), 'files': files}, separators=(',', ':'), ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


def validate_bundle(bundle):
    status = request('/api/rag/status')
    if status.get('state') != 'ready' or status.get('sourceFingerprint') != source_fingerprint():
        raise ValueError('RAG no está listo o sus fuentes cambiaron')
    if status.get('indexVersion') != bundle.get('index_version'):
        raise ValueError('Cambió la versión del índice RAG')
    result = request('/api/rag/documents')
    docs = {d['code']: d for d in result['documents']}
    chunks = {c['id']: c for c in result['chunks']}
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    citations = bundle.get('citations')
    if not isinstance(citations, list) or not 1 <= len(citations) <= 6:
        raise ValueError('RAG sin citas válidas')
    seen = set()
    for citation in citations:
        doc, chunk = docs.get(citation.get('code')), chunks.get(citation.get('id'))
        if citation.get('id') in seen or not doc or not chunk:
            raise ValueError('Cita RAG inexistente o duplicada')
        seen.add(citation['id'])
        if not doc['active'] or doc['access_role'] not in CONFIG['allowed_roles'] or doc['valid_from'] > today or (doc['valid_until'] and doc['valid_until'] < today):
            raise ValueError('Fuente RAG no vigente o no autorizada')
        if citation['sourceHash'] != doc['file_hash'] or citation['version'] != doc['version'] or chunk['document_code'] != doc['code'] or chunk['version'] != doc['version'] or citation['section'] != chunk['section'] or citation['content'] != chunk['content']:
            raise ValueError('Cita RAG no coincide con la fuente')
    return True


def retrieve_rag():
    status = request('/api/rag/status')
    if status.get('state') != 'ready':
        raise ValueError('El subagente RAG no está listo')
    result = request('/api/rag/query', {'question': CONFIG['query'], 'actor': CONFIG['actor']})
    if result.get('insufficientEvidence') is not False or not isinstance(result.get('answer'), str):
        raise ValueError('El RAG se abstuvo o devolvió un contrato inválido')
    if not result['answer'].strip() or len(result['answer']) > 6000:
        raise ValueError('Respuesta RAG vacía o demasiado extensa')
    bundle = {'agent_id': CONFIG['id'], 'version': CONFIG['version'], 'index_version': status['indexVersion'],
              'answer': result['answer'], 'citations': result.get('citations'), 'generation': result.get('generation'),
              'authority': 'documentary_context_only', 'retrieved_at': dt.datetime.now(dt.timezone.utc).isoformat()}
    validate_bundle(bundle)
    return bundle
