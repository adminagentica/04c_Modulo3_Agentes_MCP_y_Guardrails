(()=>{
const el=id=>document.getElementById(id),normalize=value=>String(value||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
let chunks=[];
function add(parent,tag,value,className){const node=document.createElement(tag);node.textContent=value;if(className)node.className=className;parent.append(node);return node;}
function render(){
  const code=el('documentFilter').value,query=normalize(el('textFilter').value.trim());
  const rows=chunks.filter(row=>(!code||row.document_code===code)&&(!query||normalize([row.id,row.document_title,row.document_code,row.version,row.section,row.content].join(' ')).includes(query)));
  el('resultCount').textContent=`${rows.length} de ${chunks.length} fragmentos.`;
  const root=el('indexRecords');root.replaceChildren();
  if(!rows.length){add(root,'p','No hay fragmentos que coincidan con los filtros.');return;}
  for(const row of rows){
    const card=document.createElement('article');card.className='panel index-record';root.append(card);
    add(card,'h2',`Fragmento ${row.id} · ${row.section}`);
    add(card,'p',`${row.document_title} (documento ${row.document_code}), ${row.version}`,'record-meta');
    add(card,'p',`Permiso: ${row.access_role} · Vigencia desde ${row.valid_from}${row.valid_until?' hasta '+row.valid_until:''}`,'record-meta');
    add(card,'h3','Texto del fragmento');add(card,'p',row.content,'chunk-text');
    add(card,'h3',`Embedding · ${row.vector.length} dimensiones`);
    add(card,'p','Primeros ocho valores, redondeados para facilitar la lectura:','note');
    add(card,'code','['+row.vector.slice(0,8).map(value=>value.toFixed(6)).join(', ')+(row.vector.length>8?', …':'')+']','vector-preview');
    const detail=document.createElement('details');card.append(detail);add(detail,'summary',`Ver el vector completo (${row.vector.length} valores)`);
    detail.addEventListener('toggle',()=>{if(detail.open&&!detail.querySelector('pre'))add(detail,'pre',JSON.stringify(row.vector,null,2),'full-vector');});
    const source=add(card,'a','Ver la sección en su documento de origen');source.href=`/rag/sources/${encodeURIComponent(row.document_code)}#chunk-${row.id}`;source.target='_blank';source.rel='noopener';
    const lineage=document.createElement('details');card.append(lineage);add(lineage,'summary','Identificación y trazabilidad');
    add(lineage,'p',`ID del registro: ${row.id}. Huella de origen del fragmento: ${row.source_hash}`,'note');
  }
}
async function load(){
  const button=el('refreshIndex');button.disabled=true;el('indexError').textContent='';
  try{
    const response=await fetch('/api/rag/index',{cache:'no-store'});if(!response.ok)throw Error('No se pudo leer el índice local. Comprueba que la demo esté activa en modo RAG local.');
    const data=await response.json();chunks=data.chunks;const meta=data.metadata||{};
    el('indexSummary').textContent=`${data.documents.length} documentos · ${chunks.length} fragmentos · ${meta.dimensions||'sin'} dimensiones por vector.`;
    const date=meta.indexedAt?new Intl.DateTimeFormat('es-PE',{dateStyle:'medium',timeStyle:'short',timeZone:'America/Lima'}).format(new Date(meta.indexedAt)):null;
    el('indexMetadata').textContent=`Modelo: ${meta.embeddingModel||'no registrado'}. Versión del índice: ${meta.indexVersion||'sin construir'}.${date?' Construido: '+date+' (Lima).':''} Estado: ${data.state}.`;
    const selected=el('documentFilter').value;el('documentFilter').replaceChildren();
    const all=add(el('documentFilter'),'option','Todos los documentos');all.value='';
    for(const document of data.documents){const option=add(el('documentFilter'),'option',`${document.title} (${document.code})`);option.value=document.code;}
    el('documentFilter').value=data.documents.some(document=>document.code===selected)?selected:'';
    render();
  }catch(error){el('indexError').textContent=error.message;el('indexSummary').textContent='No se pudo actualizar la vista.';}
  finally{button.disabled=false;}
}
el('refreshIndex').addEventListener('click',load);el('documentFilter').addEventListener('change',render);el('textFilter').addEventListener('input',render);
load();
})();
