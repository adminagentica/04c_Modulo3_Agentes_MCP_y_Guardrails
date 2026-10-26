import test from 'node:test';
import assert from 'node:assert/strict';
import {LocalRag} from '../local-rag.js';
import {generateWithOpenAI} from '../openai-generation.js';
import {prepareRagGeneration,finishRagGeneration} from '../../../demo/n8n/rag-generation-code.mjs';
const schema={type:'object',properties:{answer:{type:'string'},citationIds:{type:'array',items:{type:'integer'}},insufficientEvidence:{type:'boolean'}},required:['answer','citationIds','insufficientEvidence']};
const messages=[{role:'system',content:'Responder con evidencia'},{role:'user',content:'Pregunta documental'}];
const token='synthetic-internal-test-token-long-enough';
test('OpenAI se invoca por n8n una sola vez; no se transfiere API key',async()=>{
 let count=0;
 const result=await generateWithOpenAI(messages,schema,{token,fetch:async(url,request)=>{count++;assert.equal(url,'http://127.0.0.1:5678/webhook/agentica-rag-generate');assert.equal(request.redirect,'error');assert.equal(request.headers.Authorization,'Bearer '+token);assert.equal(JSON.stringify(JSON.parse(request.body)).includes('api_key'),false);return{ok:true,json:async()=>({content:{answer:'Respuesta [1]',citationIds:[1],insufficientEvidence:false},model:'mock-no-api',execution_id:'mock'})};}});
 assert.equal(count,1);assert.equal(result.provider,'openai');assert.equal(result.executionId,'mock');
});
test('no reintenta ni cambia de proveedor ante cuota insuficiente',async()=>{let count=0;await assert.rejects(generateWithOpenAI(messages,schema,{token,fetch:async()=>{count++;return{ok:false,json:async()=>({error:'insufficient_quota'})};}}),/credencial y el saldo/);assert.equal(count,1);});
test('rechaza webhook externo antes de invocar generación',async()=>{let calls=0;await assert.rejects(generateWithOpenAI(messages,schema,{token,url:'https://example.test/webhook',fetch:async()=>{calls++;}}),/debe ser local/);assert.equal(calls,0);});
test('rechaza salida sin contrato válido',async()=>{await assert.rejects(generateWithOpenAI(messages,schema,{token,fetch:async()=>({ok:true,json:async()=>({content:[],model:'fake'})})}),/Contrato/);});
test('workflow fija modelo, store=false y contrato estricto recursivo',()=>{
 const nested={type:'object',properties:{rows:{type:'array',items:{type:'object',properties:{value:{type:'string'}}}}}};
 const result=prepareRagGeneration({messages,schema:nested,model:'modelo-no-autorizado'}).openai_payload;
 assert.equal(result.model,'gpt-5.4-mini');assert.equal(result.store,false);assert.equal(result.max_output_tokens,1800);
 assert.equal(result.text.format.strict,true);assert.equal(result.text.format.schema.additionalProperties,false);
 assert.equal(result.text.format.schema.properties.rows.items.additionalProperties,false);
 assert.deepEqual(result.text.format.schema.properties.rows.items.required,['value']);
});
test('entrada inválida o excesiva se detiene antes del modelo',()=>{
 for(const body of [{},{messages:[{role:'assistant',content:'x'}],schema},{messages:[{role:'user',content:'x'.repeat(48001)}],schema},{messages,schema:{type:'array'}}])assert.throws(()=>prepareRagGeneration(body));
});
test('salida rechazada o incompleta no se presenta como respuesta',()=>{
 assert.equal(finishRagGeneration({statusCode:429,body:{error:{code:'insufficient_quota'}}},'test').error,'generation_failed');
 assert.equal(finishRagGeneration({body:{status:'incomplete'}},'test').error,'generation_failed');
 assert.equal(finishRagGeneration({body:{output:[{content:[{type:'refusal'}]}]}},'test').error,'generation_refused');
});
test('proveedor predeterminado OpenAI no requiere Qwen ni llama LLM al reordenar',async t=>{
 const rag=new LocalRag({dbPath:':memory:'});t.after(()=>rag.close());assert.equal(rag.generationProvider,'openai');assert.equal(rag.generationModel,'gpt-5.4-mini');
 rag.tags=async()=>[{name:rag.embeddingModel,digest:'test'}];rag.embed=async texts=>texts.map(()=>[1,.2]);await rag.start();assert.equal(rag.status().state,'ready');
 rag.chat=async()=>{throw Error('El reordenamiento no debe llamar al LLM');};const result=await rag.rerank('consulta',[{id:1},{id:2}]);assert.equal(result.model,'RRF determinista');
});
test('consulta documental completa usa una generación simulada y valida fuentes',async t=>{
 let calls=0;const rag=new LocalRag({dbPath:':memory:',openaiOptions:{token,fetch:async(_url,request)=>{calls++;const body=JSON.parse(request.body);const context=JSON.parse(body.messages[1].content);const id=context.pasajes[0].id;return{ok:true,json:async()=>({content:{answer:`Revisar condiciones [${id}].`,citationIds:[id],insufficientEvidence:false},model:'mock-no-api'})};}}});t.after(()=>rag.close());
 rag.tags=async()=>[{name:rag.embeddingModel,digest:'test'}];rag.embed=async texts=>texts.map(()=>[1,.2]);await rag.start();const result=await rag.query('¿Qué condiciones de contacto establece POL-COB-04?');assert.equal(calls,1);assert.equal(result.generation.provider,'openai');assert.equal(result.citations.length,1);
});
test('Ollama queda solo como opción explícita',async t=>{const rag=new LocalRag({dbPath:':memory:',generationProvider:'ollama'});t.after(()=>rag.close());assert.equal(rag.generationModel,'qwen3:4b');assert.throws(()=>new LocalRag({generationProvider:'desconocido'}),/Proveedor/);});
