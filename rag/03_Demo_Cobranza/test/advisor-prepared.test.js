import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const data=JSON.parse(readFileSync(new URL('../public/advisor-prepared.json',import.meta.url),'utf8'));
test('el recorrido preparado identifica la simulación y no habilita aprobación ni envíos',()=>{
  assert.equal(data.prepared,true);assert.equal(data.generation.called,false);assert.equal(data.decision.canApprove,false);
  assert.equal(data.reminder,'');assert.equal(data.executionId,undefined);
  const total=data.overdue.reduce((sum,row)=>sum+row.outstanding_amount,0);assert.equal(total,data.total);
  assert.equal(data.query.documentNumber,'74851236');assert.equal(data.query.actor,'asesor');
});
test('las citas y el contexto precargados usan los mismos IDs y el orden de fusión es coherente',()=>{
  const selected=new Set(data.rag.map(x=>x.id));
  for(const citation of data.citations){assert.ok(selected.has(citation.id));const row=data.rag.find(x=>x.id===citation.id);assert.equal(citation.content,row.content);assert.equal(citation.version,row.version);}
  for(const match of data.answer.matchAll(/\[(\d+)\]/g))assert.ok(selected.has(Number(match[1])));
  const fused=[...data.rag].sort((a,b)=>(1/(60+b.vectorRank)+1/(60+b.lexicalRank))-(1/(60+a.vectorRank)+1/(60+a.lexicalRank)));
  assert.deepEqual(fused.map(x=>x.id),data.ragPipeline.fused.map(x=>x.id));
  assert.deepEqual(data.ragPipeline.selectedIds,data.rag.map(x=>x.id));
});
