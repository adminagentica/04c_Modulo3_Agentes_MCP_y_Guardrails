import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { randomUUID } from 'node:crypto';
import { normalize } from './demo-core.js';
import {retrievalMetrics,summarizeRun,evaluateQuality,judgeRubricVersion} from './ground-truth-metrics.js';
const root=path.dirname(fileURLToPath(import.meta.url));
function bad(message,status=400){throw Object.assign(Error(message),{status});}
export class GroundTruth {
  constructor(rag){this.rag=rag;this.db=rag.db;this.db.exec('CREATE TABLE IF NOT EXISTS gt_cases(id TEXT PRIMARY KEY,payload TEXT NOT NULL);CREATE TABLE IF NOT EXISTS gt_runs(id TEXT PRIMARY KEY,payload TEXT NOT NULL);');for(const row of this.db.prepare('SELECT * FROM gt_runs').all()){const run=JSON.parse(row.payload);if(run.state==='running'){run.state='interrupted';this.saveRun(run);}}}
  async seed(){if(this.db.prepare('SELECT count(*) AS n FROM gt_cases').get().n)return;await this.rag.ensureReady();const cases=JSON.parse(await fs.readFile(path.join(root,'ground-truth/cases.json'),'utf8'));for(const c of cases)this.saveCase({...c,version:1,status:'draft',reviewer:null,reviewedAt:null,indexVersion:this.rag.metadata().indexVersion});}
  saveCase(c){this.db.exec('CREATE TABLE IF NOT EXISTS gt_case_revisions(id TEXT PRIMARY KEY,case_id TEXT,version INTEGER,payload TEXT)');const old=this.db.prepare('SELECT payload FROM gt_cases WHERE id=?').get(c.id);if(old&&old.payload!==JSON.stringify(c)){const previous=JSON.parse(old.payload);this.db.prepare('INSERT INTO gt_case_revisions VALUES(?,?,?,?)').run(randomUUID(),c.id,previous.version,old.payload);}this.db.prepare('INSERT OR REPLACE INTO gt_cases VALUES(?,?)').run(c.id,JSON.stringify(c));return c;}
  cases(){return this.db.prepare('SELECT payload FROM gt_cases ORDER BY id').all().map(r=>{const c=JSON.parse(r.payload);return {...c,stale:c.indexVersion!==this.rag.metadata()?.indexVersion};});}
  getCase(id){const row=this.db.prepare('SELECT payload FROM gt_cases WHERE id=?').get(id);if(!row)bad('Caso de referencia no encontrado.',404);return JSON.parse(row.payload);}
  verifyReferences(c){
    if(!c.expectedAbstention&&!c.expectedSources.length)bad('El caso requiere una fuente real del índice.');
    for(const expected of c.expectedSources){const rows=this.db.prepare("SELECT c.* FROM rag_chunks c JOIN rag_documents d ON d.code=c.document_code WHERE c.document_code=? AND c.version=? AND d.active=1 AND d.valid_from<=date('now') AND (d.valid_until IS NULL OR d.valid_until>=date('now'))").all(expected.code,expected.version);if(!rows.some(r=>r.section.startsWith(expected.section+' ')&&r.content.includes(expected.quote)))bad(`La evidencia de ${expected.code} ${expected.section} no coincide con el documento vigente indexado.`);}
  }
  create(body){
    const question=String(body.question||'').trim(),expectedAnswer=String(body.expectedAnswer||'').trim();if(!question||!expectedAnswer||question.length>1500||expectedAnswer.length>4000)bad('Complete pregunta y respuesta esperada con tamaños válidos.');
    const expectedAbstention=body.expectedAbstention===true,expectedSources=[];
    if(!expectedAbstention){const source=this.rag.chunk(Number(body.sourceId));if(!source||!source.active)bad('Seleccione una sección real y activa del índice.');expectedSources.push({code:source.document_code,version:source.version,section:source.section.split(' ')[0],quote:source.content});}
    const c={id:'GT-'+randomUUID().slice(0,8).toUpperCase(),version:1,question,expectedAnswer,expectedAbstention,expectedSources,points:[],status:'draft',reviewer:null,indexVersion:this.rag.metadata().indexVersion};this.verifyReferences(c);return this.saveCase(c);
  }
  validate(id,body){const c=this.getCase(id);if(body.confirmed!==true||!String(body.reviewer||'').trim())bad('Identifique al revisor y confirme que revisó pregunta, respuesta y fuente.');this.verifyReferences(c);return this.saveCase({...c,status:'validated',version:c.status==='validated'?c.version+1:c.version,reviewer:String(body.reviewer).trim().slice(0,100),approvalMode:body.approvalMode==='simulated'?'simulated':'declared',reviewedAt:new Date().toISOString(),indexVersion:this.rag.metadata().indexVersion});}
  saveRun(run){if(run.metricsVersion)run.summary=summarizeRun(run);this.db.prepare('INSERT OR REPLACE INTO gt_runs VALUES(?,?)').run(run.id,JSON.stringify(run));}
  getRun(id){const row=this.db.prepare('SELECT payload FROM gt_runs WHERE id=?').get(id);if(!row)bad('Ejecución no encontrada.',404);return JSON.parse(row.payload);}
  runs(){return this.db.prepare('SELECT payload FROM gt_runs ORDER BY rowid DESC LIMIT 10').all().map(r=>JSON.parse(r.payload));}
  start(ids,options={}){
    if(!Array.isArray(ids)||!ids.length||ids.length>20)bad('Seleccione de uno a veinte casos.');
    const k=options.k??5;if(!Number.isInteger(k)||k<1||k>10)bad('K debe ser un entero entre 1 y 10.');
    const selected=[...new Set(ids)].map(id=>this.getCase(id));for(const c of selected){this.verifyReferences(c);if(c.indexVersion!==this.rag.metadata().indexVersion)bad('Una fuente cambió. Revise y valide nuevamente el caso antes de probar.',409);}
    const evaluatorModel=process.env.GT_EVALUATOR_MODEL||this.rag.generationModel;
    const run={id:randomUUID(),state:'running',startedAt:new Date().toISOString(),indexVersion:this.rag.metadata().indexVersion,total:selected.length,metricsVersion:1,k,rankingStage:'Contexto final tras re-ranking',evaluatorModel,rubricVersion:judgeRubricVersion,results:[]};this.saveRun(run);
    void(async()=>{for(const c of selected){
      run.activeCase=c.id;run.phase='Consultando el RAG';this.saveRun(run);
      try{
        const output=await this.rag.query(c.question,['COBRANZA']);
        const sourceHit=c.expectedAbstention?null:c.expectedSources.every(e=>output.selected.some(r=>r.document_code===e.code&&r.version===e.version&&r.section.startsWith(e.section+' ')));
        const citationHit=c.expectedAbstention?null:c.expectedSources.every(e=>output.citations.some(r=>r.code===e.code&&r.version===e.version&&r.section.startsWith(e.section+' ')));
        const abstentionCorrect=output.insufficientEvidence===c.expectedAbstention;
        const pointChecks=c.points.map(point=>({point,present:normalize(output.answer).includes(normalize(point))}));
        const result={caseId:c.id,caseVersion:c.version,caseStatus:c.status,caseApprovalMode:c.approvalMode,caseReviewer:c.reviewer,expectedSources:c.expectedSources,expectedAbstention:c.expectedAbstention,actualAbstention:output.insufficientEvidence,question:c.question,expectedAnswer:c.expectedAnswer,answer:output.answer,citations:output.citations,context:output.selected.map(r=>({id:r.id,document_code:r.document_code,version:r.version,section:r.section,content:r.content,sourceHash:r.source_hash})),checks:{sourceHit,citationHit,abstentionCorrect},pointChecks,automaticPassed:abstentionCorrect&&(c.expectedAbstention||(sourceHit&&citationHit)),humanReview:null,elapsedMs:output.elapsedMs,model:output.generation.model||this.rag.generationModel,metrics:{retrieval:retrievalMetrics(c.expectedSources,output.selected,k,c.expectedAbstention),quality:{state:'pending'}}};
        run.results.push(result);run.phase='Evaluando fidelidad y completitud';this.saveRun(run);
        try{result.metrics.quality=await evaluateQuality(this.rag,c,output,evaluatorModel);}catch(error){result.metrics.quality={state:'error',error:error.message,fidelity:null,completeness:null};}
      }catch(error){run.results.push({caseId:c.id,question:c.question,expectedAbstention:c.expectedAbstention,expectedSources:c.expectedSources,error:error.message,automaticPassed:false,humanReview:null,metrics:{retrieval:retrievalMetrics(c.expectedSources,[],k,c.expectedAbstention),quality:{state:'error',error:'No se obtuvo respuesta para evaluar.',fidelity:null,completeness:null}}});}
      this.saveRun(run);
    }run.state='complete';run.activeCase=null;run.phase=null;run.finishedAt=new Date().toISOString();this.saveRun(run);})();return run;
  }
  retryQuality(runId,caseId){
    const run=this.getRun(runId);if(run.state==='running')bad('Espere a que termine la ejecución antes de reevaluar.',409);
    const result=run.results.find(r=>r.caseId===caseId);if(!result||result.error||!Array.isArray(result.context)||!result.expectedSources)bad('Esta ejecución no conserva una respuesta y contexto aptos para reevaluar. Ejecute nuevamente el caso.');
    result.qualityAttempts??=[];if(result.metrics?.quality)result.qualityAttempts.push({evaluatedAt:new Date().toISOString(),quality:result.metrics.quality,humanReview:result.humanReview});
    result.humanReview=null;result.metrics.quality={state:'pending'};run.state='running';run.activeCase=caseId;run.phase='Reevaluando la respuesta guardada';this.saveRun(run);
    void(async()=>{try{result.metrics.quality=await evaluateQuality(this.rag,result,{answer:result.answer,selected:result.context},run.evaluatorModel||this.rag.generationModel);}catch(error){result.metrics.quality={state:'error',error:error.message,fidelity:null,completeness:null};}run.state='complete';run.activeCase=null;run.phase=null;run.reevaluatedAt=new Date().toISOString();this.saveRun(run);})();return run;
  }
  review(runId,caseId,body){const run=this.getRun(runId),result=run.results.find(r=>r.caseId===caseId);if(!result)bad('Resultado no encontrado.',404);if(!['pass','fail'].includes(body.verdict)||!String(body.reviewer||'').trim())bad('Indique revisor y resultado de la revisión.');if(body.verdict==='pass'&&!result.automaticPassed)bad('Hay fallos objetivos de fuente, cita o abstención. Corrija y vuelva a ejecutar antes de aprobar.');result.humanReview={verdict:body.verdict,reviewer:String(body.reviewer).trim().slice(0,100),notes:String(body.notes||'').slice(0,2000),reviewedAt:new Date().toISOString()};this.saveRun(run);return run;}
}
