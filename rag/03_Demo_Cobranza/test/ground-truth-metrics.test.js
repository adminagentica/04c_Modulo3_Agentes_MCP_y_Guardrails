import test from 'node:test';
import assert from 'node:assert/strict';
import {retrievalMetrics,summarizeRun,evaluateQuality} from '../ground-truth-metrics.js';
const expected=[{code:'POL-PAG-02',version:'v5',section:'§4'},{code:'POL-PAG-02',version:'v5',section:'§5'}];
const row=(id,section,version='v5')=>({id,document_code:'POL-PAG-02',version,section,content:'Texto'});
test('ranking y denominadores de Precision, Recall, Hit y RR@K',()=>{
  const ranked=[row(1,'§1 Otro'),row(2,'§4 Conciliación'),row(3,'§5 Reanudación')];
  const m=retrievalMetrics(expected,ranked,3);assert.equal(m.precisionAtK,2/3);assert.equal(m.recallAtK,1);assert.equal(m.hitAtK,1);assert.equal(m.reciprocalRankAtK,.5);
  const one=retrievalMetrics(expected,ranked,1);assert.equal(one.recallAtK,0);assert.equal(one.hitAtK,0);assert.equal(one.reciprocalRankAtK,0);
  assert.equal(retrievalMetrics(expected,[row(1,'§4 Conciliación','v4')],3).hitAtK,0);
});
test('no infla recall con duplicados y las posiciones vacías cuentan cero',()=>{
  const m=retrievalMetrics(expected,[row(1,'§4 Conciliación'),row(1,'§4 Conciliación')],5);assert.equal(m.precisionAtK,.2);assert.equal(m.recallAtK,.5);assert.equal(m.returned,1);
  assert.equal(retrievalMetrics([],[],5,true).hitAtK,null);
});
test('MRR es promedio por caso y abstención usa solo casos sin evidencia',()=>{
  const q={state:'complete',fidelity:1,completeness:.5};
  const run={total:3,results:[{expectedAbstention:false,checks:{citationHit:true},metrics:{retrieval:retrievalMetrics(expected,[row(1,'§4 Conciliación')],3),quality:q}},{expectedAbstention:false,error:'fallo',metrics:{retrieval:retrievalMetrics(expected,[],3),quality:{state:'error'}}},{expectedAbstention:true,checks:{abstentionCorrect:true},metrics:{retrieval:retrievalMetrics([],[],3,true),quality:{state:'not_applicable'}}}]};
  const s=summarizeRun(run);assert.equal(s.mrrAtK,.5);assert.equal(s.correctAbstentionRate,1);assert.equal(s.qualityCases,1);assert.equal(s.errors,1);assert.equal(s.completeness,.5);
});
test('una negación respaldada puede ser fiel y estar incompleta',async()=>{
  const rag={generationModel:'local',chat:async()=>({content:{claims:[{text:'No puede continuar',quote:'No',supported:true,evidenceIds:[16],reason:'La sección lo prohíbe'}],requirements:[{text:'No continuar',answerQuote:'No',covered:true,reason:'Lo niega'},{text:'Requiere intervención humana',answerQuote:'',covered:false,reason:'No explica intervención'}]},model:'local'})};
  const q=await evaluateQuality(rag,{question:'¿Puede continuar?',expectedAnswer:'No. Requiere intervención humana.',expectedSources:[{code:'POL-PAG-02',version:'v5',section:'§3',quote:'Texto'}]},{answer:'No',selected:[row(16,'§3 Atención especial')]},'local');assert.equal(q.fidelity,1);assert.equal(q.completeness,.5);assert.equal(q.evaluationMethod,'binary_reference');
});
test('no acepta respaldo del evaluador con citas ajenas al contexto',async()=>{
  const rag={chat:async()=>({content:{claims:[{unitId:1,supported:true,evidenceIds:[999],reason:'No válido'}],requirements:[{text:'Requisito',covered:true,reason:'Texto'}]}})};
  await assert.rejects(evaluateQuality(rag,{question:'Pregunta',expectedAnswer:'Respuesta'},{answer:'Texto',selected:[row(1,'§1')]},'local'),/evidencia válida/);
});
test('separa fidelidad y completitud y exige citas literales de la salida',async()=>{
  let calls=0;
  const answer='Pausar contacto y derivar a Operaciones.';
  const rag={generationModel:'local',chat:async(messages,schema)=>{
    calls++;const payload=JSON.parse(messages[1].content);
    if(schema.properties.claims){assert.ok(payload.contexto);assert.equal(payload.RESPUESTA_ESPERADA,undefined);return{model:'local',content:{claims:[{unitId:1,supported:true,evidenceIds:[11],reason:'Fuente real'}]}};}
    assert.equal(payload.contexto,undefined);assert.ok(payload.RESPUESTA_ESPERADA);
    return{model:'local',content:{requirements:[{text:'Pausar contacto',covered:true,answerQuote:answer,reason:'Incluido'},{text:'Derivar a Operaciones',covered:true,answerQuote:answer,reason:'Incluido'}]}};
  }};
  const q=await evaluateQuality(rag,{question:'¿Qué hacer?',expectedAnswer:answer},{answer,selected:[row(11,'§4 Conciliación')]},'local');assert.equal(calls,2);assert.equal(q.fidelity,1);assert.equal(q.completeness,1);
  rag.chat=async()=>({content:{claims:[{unitId:999,supported:true,evidenceIds:[11],reason:'Falso'}]}});
  await assert.rejects(evaluateQuality(rag,{question:'Pregunta',expectedAnswer:answer},{answer,selected:[row(11,'§4')]},'local'),/unidades/);
});
