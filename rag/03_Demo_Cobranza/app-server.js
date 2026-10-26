import express from 'express';
import pg from 'pg';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { randomUUID, createHash } from 'node:crypto';
import { analyze } from './demo-core.js';
import { fixtureRepository, postgresRepository } from './demo-repository.js';
import { LocalRag } from './local-rag.js';
import { GroundTruth } from './ground-truth.js';

const root = path.dirname(fileURLToPath(import.meta.url));
const actors = { asesor: { label:'Asesor de Cobranzas', roles:['COBRANZA'] }, supervisor: { label:'Supervisor de Cobranzas', roles:['COBRANZA','SUPERVISION'] } };
function fail(status, message) { const error = new Error(message); error.status = status; throw error; }
function reviewSnapshot(result) {
  return createHash('sha256').update(JSON.stringify({customer:result.customer,overdue:result.overdue,history:result.history,citations:result.citations,decision:result.decision.code})).digest('hex');
}

export function createApp(options = {}) {
  const app = express();
  const localRag=options.localRag||(process.env.RAG_MODE==='local'&&!options.repository?new LocalRag():null);
  const groundTruth=localRag?new GroundTruth(localRag):null;
  const pool = options.pool || (localRag || options.repository || process.env.DEMO_DATA_MODE === 'fixtures' ? null : new pg.Pool({ connectionString:process.env.DATABASE_URL || 'postgres://cobranza:cobranza_demo@localhost:5433/cobranza_demo' }));
  const repository = options.repository || localRag?.repository || (pool ? postgresRepository(pool) : fixtureRepository());
  const runAnalysis=input=>localRag?localRag.analyze(input):analyze(repository,input);
  if(localRag)void localRag.start().then(()=>groundTruth.seed()).catch(error=>console.error('RAG local:',error.message));
  const gatewayFetch = options.gatewayFetch || fetch;
  const gateway = options.gatewayUrl || process.env.WHATSAPP_GATEWAY_URL || 'http://127.0.0.1:5200';
  const delivery = options.deliveryMode || process.env.WHATSAPP_DELIVERY_MODE || 'preview';
  const executions = new Map();
  const ttl = 15 * 60 * 1000;
  app.use(express.json({ limit:'24kb' }));
  app.get('/favicon.ico',(_req,res)=>res.status(204).end());
  app.get('/',(_req,res)=>res.sendFile(path.join(root,'public/lesson33.html')));
  app.get('/index.html',(_req,res)=>res.redirect('/'));
  app.use(express.static(path.join(root,'public')));

  function execution(id) {
    const item=executions.get(id);
    if(!item || item.expires<Date.now()) { if(item)executions.delete(id);fail(409,'Ejecute nuevamente la consulta. La revisión venció o no existe.'); }
    return item;
  }
  async function refresh(item) {
    const result=localRag?await localRag.revalidate(item.result,item.input):await runAnalysis(item.input);
    if(!result.decision.canApprove)fail(409,`Acción bloqueada: ${result.decision.label}. ${result.decision.reason}`);
    if(reviewSnapshot(result)!==item.snapshot)fail(409,'Los datos o la política cambiaron. Ejecute nuevamente el caso y revise la nueva propuesta.');
    return result;
  }
  function destination(result,channel,to) {
    if(!['EMAIL','WHATSAPP'].includes(channel) || channel!==result.customer.preferredChannel)fail(403,'El canal no está autorizado para este caso en el CRM.');
    const expected=channel==='WHATSAPP'?result.customer.whatsapp:result.customer.email;
    const normalized=channel==='WHATSAPP'?String(to||'').replace(/\D/g,''):String(to||'').trim().toLowerCase();
    if(!expected || normalized!==String(expected).toLowerCase())fail(403,'El destinatario debe coincidir con el contacto autorizado en el CRM.');
    return normalized;
  }
  async function approvedRequest(body,channel) {
    const item=execution(body.executionId), approval=item.approval;
    if(!approval || approval.id!==body.approvalId || approval.used)fail(409,'Falta una aprobación vigente para esta acción y este mensaje.');
    if(approval.channel!==channel || approval.text!==String(body.text||'').trim() || approval.to!==String(body.to||'').trim())fail(409,'Cambió el canal, el mensaje o el destinatario. Solicite una nueva aprobación.');
    // Reserve before awaiting the fresh lookup so concurrent requests cannot reuse approval.
    approval.used=true;
    const result=await refresh(item);
    destination(result,channel,body.to);
    return {item,approval,result};
  }

  app.get('/api/health',async(_req,res)=>{
    try {
      if(pool)await pool.query('SELECT 1');
      res.json({ok:true,database:repository.mode,ragMode:localRag?'local':'didactic',rag:localRag?.status(),deliveryMode:delivery,implementation:localRag?`DOCX, embeddings locales e índice SQLite; generación ${localRag.generationProvider==='openai'?'OpenAI mediante n8n':'Ollama'}.`:'Orquestación y respuesta por reglas; embeddings de cuatro dimensiones y re-ranking didácticos.'});
    }catch{res.status(503).json({ok:false,database:'unavailable',error:'PostgreSQL no está disponible. Inicie la base o use npm run demo:clase.'});}
  });

  app.post('/api/cobranza/search',async(req,res,next)=>{
    try {
      const {documentType,documentNumber,query='Revisar deuda y preparar recordatorio',actor='asesor'}=req.body;
      const number=String(documentNumber||'');
      if(!((documentType==='DNI'&&/^\d{8}$/.test(number))||(documentType==='RUC'&&/^\d{11}$/.test(number))))fail(400,'Ingrese un DNI de 8 dígitos o un RUC de 11 dígitos del demo.');
      if(typeof query!=='string'||!query.trim()||query.length>1500)fail(400,'Ingrese una consulta de hasta 1500 caracteres.');
      if(!actors[actor])fail(400,'Seleccione un perfil de la demostración.');
      const input={documentType,documentNumber:number,query:query.trim(),actor,roles:actors[actor].roles};
      const result=await runAnalysis(input);
      for(const [id,item] of executions)if(item.expires<Date.now())executions.delete(id);
      if(executions.size>=500)executions.delete(executions.keys().next().value);
      const id=randomUUID();executions.set(id,{input,result:localRag?result:null,expires:Date.now()+ttl,approval:null,snapshot:reviewSnapshot(result)});
      res.json({...result,executionId:id,actor:actors[actor].label,deliveryMode:delivery});
    }catch(error){next(error);}
  });

  app.post('/api/cobranza/approve',async(req,res,next)=>{
    try {
      if(req.body.confirmed!==true)fail(400,'Debe confirmar la revisión humana de la propuesta.');
      const item=execution(req.body.executionId),result=await refresh(item);
      const channel=req.body.channel,to=destination(result,channel,req.body.to),text=String(req.body.text||'').trim();
      if(!text||text.length>1000)fail(400,'El mensaje debe tener entre 1 y 1000 caracteres.');
      const approval={id:randomUUID(),channel,to,text,used:false};item.approval=approval;
      res.json({ok:true,approvalId:approval.id,channel,to,deliveryMode:delivery});
    }catch(error){next(error);}
  });

  app.post('/api/reminders/whatsapp',async(req,res,next)=>{
    try {
      const {approval}=await approvedRequest(req.body,'WHATSAPP');
      approval.used=true;
      if(delivery!=='gateway')return res.json({ok:true,simulated:true,result:{to:approval.to,text:approval.text},message:'Simulación completada. No se envió ningún mensaje externo.'});
      const headers={'Content-Type':'application/json'};
      if(process.env.WHATSAPP_INTERNAL_TOKEN)headers['X-Internal-Token']=process.env.WHATSAPP_INTERNAL_TOKEN;
      const response=await gatewayFetch(`${gateway}/internal/whatsapp/send`,{method:'POST',headers,body:JSON.stringify({to:approval.to,text:approval.text}),signal:AbortSignal.timeout(8000)});
      const raw=await response.text();let result;try{result=JSON.parse(raw);}catch{result={detail:raw.slice(0,500)};}
      if(!response.ok)fail(502,result.detail||'El gateway no aceptó el mensaje. Revise el resultado antes de volver a aprobar.');
      res.json({ok:true,simulated:false,result});
    }catch(error){next(error);}
  });

  app.post('/api/reminders/email-draft',async(req,res,next)=>{
    try {
      const {approval}=await approvedRequest(req.body,'EMAIL');
      approval.used=true;
      res.json({ok:true,simulated:true,mailto:`mailto:${encodeURIComponent(approval.to)}?subject=${encodeURIComponent('Recordatorio de pago')}&body=${encodeURIComponent(approval.text)}`});
    }catch(error){next(error);}
  });
  if(localRag){
    const safe=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    app.get('/api/rag/status',(_req,res)=>res.json(localRag.status()));
    app.post('/api/rag/ingest',(_req,res)=>{void localRag.start(true).then(()=>groundTruth.seed()).catch(error=>console.error('Ingesta:',error.message));res.status(202).json(localRag.status());});
    app.get('/api/rag/documents',(_req,res)=>res.json({documents:localRag.documents(),chunks:localRag.db.prepare('SELECT id,document_code,version,section,content FROM rag_chunks ORDER BY id').all()}));
    app.get('/api/rag/index',(_req,res)=>{
      const chunks=localRag.db.prepare('SELECT c.id,c.document_code,c.version,c.section,c.title,c.content,c.embedding,c.source_hash,d.title AS document_title,d.access_role,d.valid_from,d.valid_until FROM rag_chunks c JOIN rag_documents d ON d.code=c.document_code ORDER BY c.id').all().map(({embedding,...row})=>({...row,vector:JSON.parse(embedding)}));
      res.set('Cache-Control','no-store').json({metadata:localRag.metadata(),state:localRag.state,documents:localRag.documents(),chunks});
    });
    app.get('/api/rag/files/:code',(req,res,next)=>{const doc=localRag.documents().find(d=>d.code===req.params.code);if(!doc)return res.status(404).json({error:'Documento no registrado.'});res.download(path.join(localRag.corpus,doc.source_file),doc.source_file,error=>{if(error)next(error);});});
    app.get('/rag/sources/:code',(req,res)=>{const doc=localRag.documents().find(d=>d.code===req.params.code);if(!doc)return res.status(404).send('Documento no registrado.');const chunks=localRag.db.prepare('SELECT id,section,content FROM rag_chunks WHERE document_code=? ORDER BY id').all(doc.code);res.type('html').send(`<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${safe(doc.title)}</title><link rel="stylesheet" href="/styles.css"><main style="display:block;max-width:900px"><a href="/">Volver a la demo</a><h1>${safe(doc.title)}</h1><p>${safe(doc.code)} ${safe(doc.version)} · permiso ${safe(doc.access_role)} · vigente desde ${safe(doc.valid_from)}</p><p><a href="/api/rag/files/${safe(doc.code)}">Abrir documento Word original</a></p><p class="note">SHA-256 del archivo: ${safe(doc.file_hash)}</p>${chunks.map(c=>`<section class="panel" id="chunk-${c.id}"><h2>[${c.id}] ${safe(c.section)}</h2><p>${safe(c.content)}</p></section>`).join('')}</main></html>`);});
    app.post('/api/rag/query',async(req,res,next)=>{try{const question=String(req.body.question||'').trim();if(!question||question.length>1500)fail(400,'Ingrese una pregunta de hasta 1500 caracteres.');const actor=actors[req.body.actor||'asesor'];if(!actor)fail(400,'Perfil inválido.');const result=await localRag.query(question,actor.roles);res.json({...result,retrieval:{metadata:result.retrieval.metadata,fused:result.retrieval.fused,queryVectorPreview:result.retrieval.queryVector.slice(0,8)},reranker:{rows:result.reranker.rows,durationMs:result.reranker.durationMs}});}catch(error){next(error);}});
    app.get('/api/ground-truth/cases',async(_req,res,next)=>{try{await groundTruth.seed();res.json({cases:groundTruth.cases()});}catch(error){next(error);}});
    app.post('/api/ground-truth/cases',(req,res,next)=>{try{res.status(201).json(groundTruth.create(req.body));}catch(error){next(error);}});
    app.post('/api/ground-truth/cases/:id/validate',(req,res,next)=>{try{res.json(groundTruth.validate(req.params.id,req.body));}catch(error){next(error);}});
    app.post('/api/ground-truth/runs',(req,res,next)=>{try{res.status(202).json(groundTruth.start(req.body.caseIds,{k:req.body.k}));}catch(error){next(error);}});
    app.get('/api/ground-truth/runs',(_req,res)=>res.json({runs:groundTruth.runs()}));
    app.get('/api/ground-truth/runs/:id',(req,res,next)=>{try{res.json(groundTruth.getRun(req.params.id));}catch(error){next(error);}});
    app.post('/api/ground-truth/runs/:id/retry-quality',(req,res,next)=>{try{res.status(202).json(groundTruth.retryQuality(req.params.id,req.body.caseId));}catch(error){next(error);}});
    app.post('/api/ground-truth/runs/:id/review',(req,res,next)=>{try{res.json(groundTruth.review(req.params.id,req.body.caseId,req.body));}catch(error){next(error);}});
  }
  app.use((error,_req,res,_next)=>{res.status(error.status||500).json({error:error.status||localRag?error.message:'No se pudo completar la consulta. Verifique la conexión y el esquema de la base de datos.'});});
  app.locals.close=async()=>{if(localRag){if(localRag.job)await localRag.job.catch(()=>{});localRag.close();}await pool?.end();};
  app.locals.localRag=localRag;
  return app;
}
