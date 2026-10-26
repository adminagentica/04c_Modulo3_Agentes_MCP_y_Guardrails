import test from 'node:test';
import assert from 'node:assert/strict';
import { analyze, fuseAndRerank } from '../demo-core.js';
import { fixtureRepository } from '../demo-repository.js';
import { createApp } from '../app-server.js';

const input=(number='74851236',type='DNI',query='Revisar deuda y preparar recordatorio')=>({documentType:type,documentNumber:number,query,roles:['COBRANZA'],actor:'asesor'});
test('casos del guion: propuesta, conciliación, atención especial, promesa y abstención',async()=>{
  for(const [i,code] of [[input(),'READY_FOR_REVIEW'],[input('20548796321','RUC'),'PAUSE_AND_RECONCILE'],[input('40112233'),'HUMAN_ATTENTION'],[input('71234567'),'HUMAN_REVIEW'],[input('74851236','DNI','Según POL-SIN-99, ¿puedo contactar?'),'INSUFFICIENT_EVIDENCE']]){
    const d=await analyze(fixtureRepository(),i);assert.equal(d.decision.code,code);assert.equal(d.decision.canApprove,code==='READY_FOR_REVIEW');
    if(code==='PAUSE_AND_RECONCILE')assert.equal(d.citations[0].code,'POL-PAG-02');
  }
});
test('el estado del pago tiene prioridad sobre la promesa incumplida',async()=>{const d=await analyze(fixtureRepository(),input('20548796321','RUC'));assert.equal(d.decision.code,'PAUSE_AND_RECONCILE');assert.equal(d.reminder,'');});
test('ambas rutas excluyen fuentes restringidas, futuras, vencidas o retiradas',async()=>{
  for(const override of [{active:false},{access_role:'SUPERVISION'},{valid_from:'2999-01-01'},{valid_until:'2000-01-01'}]){
    const repo=fixtureRepository();Object.assign(repo.policies[0],override);const d=await analyze(repo,input());
    assert.equal(d.decision.code,'INSUFFICIENT_EVIDENCE');
    assert.ok(![...d.ragPipeline.vectorCandidates,...d.ragPipeline.lexicalCandidates].some(x=>x.document_code==='POL-COB-04'));
  }
});
test('RRF consolida por ID y el re-ranking queda separado de la fusión',()=>{
  const a={id:1,document_code:'A',content:'pago'},b={id:2,document_code:'B',content:'conciliación'};
  const {fused,reranked}=fuseAndRerank([a,b],[a,b],'pago','B');assert.equal(fused.length,2);assert.equal(fused[0].id,1);assert.equal(reranked[0].id,2);assert.equal(reranked[0].fusionRank,2);
});
test('sin deuda vencida no se prepara contacto',async()=>{const repo=fixtureRepository();repo.debts[0].status='PAID';const d=await analyze(repo,input());assert.equal(d.decision.code,'NO_OVERDUE');assert.equal(d.decision.canApprove,false);});

async function harness(t,options={}){
  const repository=fixtureRepository();let gatewayCalls=0;
  const app=createApp({repository,deliveryMode:options.deliveryMode||'preview',gatewayFetch:async()=>{gatewayCalls++;return new Response(JSON.stringify({ok:true}),{status:200});}});
  const server=app.listen(0,'127.0.0.1');await new Promise((resolve,reject)=>{server.once('listening',resolve);server.once('error',reject);});
  t.after(()=>new Promise(resolve=>server.close(resolve)));
  const base=`http://127.0.0.1:${server.address().port}`;
  async function post(route,body){const r=await fetch(base+route,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});return{status:r.status,data:await r.json()};}
  const search=async(i=input())=>(await post('/api/cobranza/search',i)).data;
  const approve=async(d,changes={})=>post('/api/cobranza/approve',{executionId:d.executionId,confirmed:true,channel:'WHATSAPP',to:d.customer.whatsapp,text:d.reminder,...changes});
  return{repository,base,post,search,approve,gatewayCalls:()=>gatewayCalls};
}
test('API rechaza DNI/RUC de longitud incorrecta',async t=>{const h=await harness(t);assert.equal((await h.post('/api/cobranza/search',input('123456789'))).status,400);assert.equal((await h.post('/api/cobranza/search',input('12345678','RUC'))).status,400);});
test('un envío directo o un caso en pausa no puede omitir la aprobación',async t=>{
  const h=await harness(t);assert.equal((await h.post('/api/reminders/whatsapp',{to:'51999900001',text:'prueba'})).status,409);
  const d=await h.search(input('20548796321','RUC'));assert.equal((await h.approve(d)).status,409);assert.equal(h.gatewayCalls(),0);
});
test('aprobación requiere confirmación humana y canal y contacto del CRM',async t=>{
  const h=await harness(t),d=await h.search();
  assert.equal((await h.approve(d,{confirmed:false})).status,400);
  assert.equal((await h.approve(d,{to:'51911111111'})).status,403);
  assert.equal((await h.approve(d,{channel:'EMAIL',to:d.customer.email})).status,403);
});
test('el mensaje modificado exige una nueva aprobación',async t=>{
  const h=await harness(t),d=await h.search(),a=await h.approve(d);assert.equal(a.status,200);
  assert.equal((await h.post('/api/reminders/whatsapp',{executionId:d.executionId,approvalId:a.data.approvalId,to:d.customer.whatsapp,text:'otro texto'})).status,409);assert.equal(h.gatewayCalls(),0);
});
test('el servidor vuelve a comprobar el estado del pago antes de enviar',async t=>{
  const h=await harness(t),d=await h.search(),a=await h.approve(d);
  h.repository.events.push({customer_id:1,event_type:'PAYMENT',status:'PENDING_RECONCILIATION'});
  assert.equal((await h.post('/api/reminders/whatsapp',{executionId:d.executionId,approvalId:a.data.approvalId,to:d.customer.whatsapp,text:d.reminder})).status,409);assert.equal(h.gatewayCalls(),0);
});
test('un saldo o una política modificados exigen revisar una nueva ejecución',async t=>{
  for(const change of [repo=>{repo.debts[0].outstanding_amount=2000;},repo=>{repo.policies[0].version='v4';}]){
    const h=await harness(t),d=await h.search(),a=await h.approve(d);change(h.repository);
    assert.equal((await h.post('/api/reminders/whatsapp',{executionId:d.executionId,approvalId:a.data.approvalId,to:d.customer.whatsapp,text:d.reminder})).status,409);assert.equal(h.gatewayCalls(),0);
  }
});
test('modo de clase simula el envío y no reutiliza la aprobación',async t=>{
  const h=await harness(t),d=await h.search(),a=await h.approve(d),payload={executionId:d.executionId,approvalId:a.data.approvalId,to:d.customer.whatsapp,text:d.reminder};
  const sent=await h.post('/api/reminders/whatsapp',payload);assert.equal(sent.status,200);assert.equal(sent.data.simulated,true);
  assert.equal((await h.post('/api/reminders/whatsapp',payload)).status,409);assert.equal(h.gatewayCalls(),0);
});
test('peticiones simultáneas no duplican una llamada al gateway',async t=>{
  const h=await harness(t,{deliveryMode:'gateway'}),d=await h.search(),a=await h.approve(d),payload={executionId:d.executionId,approvalId:a.data.approvalId,to:d.customer.whatsapp,text:d.reminder};
  const results=await Promise.all([h.post('/api/reminders/whatsapp',payload),h.post('/api/reminders/whatsapp',payload)]);
  assert.deepEqual(results.map(x=>x.status).sort(),[200,409]);assert.equal(h.gatewayCalls(),1);
});
test('correo autorizado genera un borrador, sin envío automático',async t=>{
  const h=await harness(t),d=await h.search(input('20601234567','RUC')),a=await h.approve(d,{channel:'EMAIL',to:d.customer.email});assert.equal(a.status,200);
  const r=await h.post('/api/reminders/email-draft',{executionId:d.executionId,approvalId:a.data.approvalId,to:d.customer.email,text:d.reminder});assert.equal(r.status,200);assert.ok(r.data.mailto.startsWith('mailto:'));assert.equal(h.gatewayCalls(),0);
});
