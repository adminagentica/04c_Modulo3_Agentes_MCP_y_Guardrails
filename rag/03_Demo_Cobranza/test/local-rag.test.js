import test from 'node:test';
import assert from 'node:assert/strict';
import { LocalRag, cosine, sectionsFromParagraphs } from '../local-rag.js';
import { GroundTruth } from '../ground-truth.js';

async function testIndex(t){
  const rag=new LocalRag({dbPath:':memory:'});
  // Unit tests isolate model I/O; separate end-to-end runs use the installed Ollama models.
  rag.tags=async()=>[{name:rag.embeddingModel,digest:'unit-test-embedding'},{name:rag.generationModel,digest:'unit-test-generation'}];
  rag.embed=async texts=>texts.map(()=>[1,.5,.2]);
  await rag.start();t.after(()=>rag.close());return rag;
}
test('ingesta lee los cuatro DOCX existentes y persiste 26 secciones con huellas',async t=>{const rag=await testIndex(t);assert.equal(rag.documents().length,4);assert.equal(rag.metadata().chunkCount,26);assert.ok(rag.documents().every(d=>d.file_hash.length===64&&d.source_file.endsWith('.docx')));assert.equal(rag.db.prepare('SELECT count(*) AS n FROM rag_fts').get().n,26);});
test('una reconstrucción fallida no borra el índice anterior',async t=>{const rag=await testIndex(t),version=rag.metadata().indexVersion;rag.embed=async()=>{throw Error('fallo de modelo de prueba');};await assert.rejects(rag.start(true),/fallo de modelo/);assert.equal(rag.metadata().indexVersion,version);assert.equal(rag.db.prepare('SELECT count(*) AS n FROM rag_chunks').get().n,26);});
test('búsqueda filtra permisos antes de devolver resultados de ambas rutas',async t=>{const rag=await testIndex(t);rag.db.prepare("UPDATE rag_documents SET access_role='SUPERVISION' WHERE code='POL-PAG-02'").run();const r=await rag.retrieve('pago pendiente de conciliación',['COBRANZA']);assert.ok(![...r.vector,...r.lexical].some(x=>x.document_code==='POL-PAG-02'));});
test('la respuesta generada no puede citar un ID ajeno al contexto',async t=>{const rag=await testIndex(t);rag.chat=async(_messages,schema)=>({content:schema.properties.ids?{ids:[20]}:{answer:'Texto inválido',citationIds:[999],insufficientEvidence:false},model:'modelo de prueba'});await assert.rejects(rag.query('promesa de pago'),/citas válidas/);});
test('fragmentación conserva sección y comparación rechaza dimensiones incompatibles',()=>{assert.equal(sectionsFromParagraphs(['Reglas y procedimientos','4 Conciliación','Pausar contacto.','Controles del sistema RAG'])[0].section,'§4 Conciliación');assert.throws(()=>cosine([1,2],[1]),/incompatibles/);});
test('Ground Truth requiere fuentes reales y validación humana identificada',async t=>{
  const rag=await testIndex(t),gt=new GroundTruth(rag);await gt.seed();assert.equal(gt.cases().length,4);assert.ok(gt.cases().every(c=>c.status==='draft'));for(const c of gt.cases())gt.verifyReferences(c);
  assert.throws(()=>gt.validate('GT-PRO-01',{confirmed:false,reviewer:'Revisor de pruebas'}),/confirme/);
  assert.throws(()=>gt.create({question:'Pregunta',expectedAnswer:'Respuesta',sourceId:999}),/sección real/);
  const c=gt.validate('GT-PRO-01',{confirmed:true,reviewer:'Revisor de pruebas'});assert.equal(c.status,'validated');
  assert.throws(()=>gt.start(['GT-PRO-01'],{k:0}),/K debe/);
  rag.query=async()=>({answer:c.expectedAnswer,selected:[rag.chunk(20)],citations:[{id:20,code:'POL-PRO-03',version:c.expectedSources[0].version,section:'§1 Registro de la promesa'}],insufficientEvidence:false,generation:{model:'doble de prueba'},elapsedMs:1});
  rag.chat=async()=>({content:{claims:[{unitId:1,supported:true,evidenceIds:[20],reason:'Fuente de prueba'}],requirements:[{text:c.expectedAnswer,answerQuote:c.expectedAnswer,covered:true,reason:'Cobertura de prueba'}]},model:'evaluador de prueba'});
  const run=gt.start(['GT-PRO-01']);for(let i=0;i<50&&gt.getRun(run.id).state==='running';i++)await new Promise(resolve=>setTimeout(resolve,2));
  const result=gt.getRun(run.id);assert.equal(result.state,'complete');assert.equal(result.results[0].automaticPassed,true);assert.equal(result.results[0].humanReview,null);
  assert.equal(result.k,5);assert.equal(result.summary.recallAtK,1);assert.equal(result.summary.mrrAtK,1);assert.equal(result.summary.fidelity,1);assert.equal(result.summary.completeness,1);assert.ok(result.results[0].context.length);
  assert.throws(()=>gt.review(run.id,'GT-PRO-01',{verdict:'pass',reviewer:''}),/revisor/);assert.equal(gt.review(run.id,'GT-PRO-01',{verdict:'pass',reviewer:'Revisor de pruebas'}).results[0].humanReview.verdict,'pass');
  rag.query=async()=>{throw Error('Reevaluar no debe consultar el RAG');};
  gt.retryQuality(run.id,'GT-PRO-01');for(let i=0;i<50&&gt.getRun(run.id).state==='running';i++)await new Promise(resolve=>setTimeout(resolve,2));
  const retried=gt.getRun(run.id);assert.equal(retried.results[0].metrics.quality.state,'complete');assert.equal(retried.results[0].qualityAttempts.length,1);assert.equal(retried.results[0].humanReview,null);assert.equal(retried.results[0].qualityAttempts[0].humanReview.verdict,'pass');
});
test('aprobación docente simulada conserva su etiqueta y la revisión anterior',async t=>{
  const rag=await testIndex(t),gt=new GroundTruth(rag);await gt.seed();
  const c=gt.validate('GT-PRO-01',{confirmed:true,reviewer:'Experto docente simulado',approvalMode:'simulated'});
  assert.equal(c.approvalMode,'simulated');assert.equal(c.status,'validated');
  const previous=rag.db.prepare('SELECT payload FROM gt_case_revisions WHERE case_id=?').all(c.id).map(r=>JSON.parse(r.payload));
  assert.ok(previous.some(r=>r.status==='draft'));assert.equal(gt.getCase(c.id).expectedSources[0].version,rag.chunk(20).version);
});
