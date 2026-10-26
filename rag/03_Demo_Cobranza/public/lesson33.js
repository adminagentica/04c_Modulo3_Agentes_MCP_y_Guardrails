const $ = id => document.getElementById(id);
const h = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money = value => `S/ ${Number(value).toFixed(2)}`;
let current = null, approval = null, stale = false, stageIndex = 0, realRag = false, pending = false, inputRevision = 0;
const stages = [
  {name:'Asesor y orquestador',input:'DNI o RUC, consulta e identidad del asesor.',process:'Separa la necesidad de datos operativos de la consulta documental.',output:'Consultas coordinadas a las fuentes de la diapositiva.',note:'Los especialistas de esta demo son funciones del programa; no son agentes LLM independientes.'},
  {name:'Datos operativos',input:'Identificador del cliente.',process:'Deuda, historial y cliente consultan sus fuentes. Los montos no se buscan en embeddings.',output:'Saldo exacto, pagos o promesas y contacto autorizado.',note:'Estos datos proceden de PostgreSQL o de los casos incorporados, según el modo indicado arriba.'},
  {name:'Embedding de consulta',input:'Pregunta original y señales operativas del caso.',process:'Normaliza el texto y genera una representación de cuatro dimensiones mediante reglas didácticas.',output:'Vector comparable con los vectores del corpus docente.',note:'Esta representación no es un modelo entrenado. En una solución real se usa un modelo de embeddings compatible con el índice.'},
  {name:'Búsqueda híbrida y fusión',input:'Texto, vector y permisos del perfil de clase.',process:'Busca por similitud y por términos. Filtra documentos permitidos y vigentes, y fusiona posiciones con RRF.',output:'Una lista de candidatos con ID, fuente, versión y sección.',note:'PostgreSQL usa full-text con ts_rank_cd. El modo sin base simula esa ruta con coincidencias de palabras. Ninguna se presenta como BM25.'},
  {name:'Re-ranking y contexto',input:'Lista fusionada y estado operativo del caso.',process:'Un segundo ordenamiento didáctico prioriza la política aplicable y selecciona hasta cuatro pasajes.',output:'Contexto con contenido y citas verificables.',note:'El re-ranking usa reglas visibles, no un modelo neuronal. Una puntuación alta no demuestra verdad.'},
  {name:'¿Se puede actuar?',input:'Datos operativos, políticas recuperadas y controles de negocio.',process:'Comprueba pago pendiente, atención especial, promesa incumplida, alcance y evidencia suficiente.',output:'Preparar una propuesta para revisión o bloquear y escalar.',note:'Un pago pendiente bloquea el contacto aunque exista deuda vencida. La falta de evidencia también bloquea la acción.'},
  {name:'Respuesta fundamentada',input:'Datos exactos y pasajes seleccionados.',process:'Construye una explicación con documento, versión y sección.',output:'Decisión propuesta y fuente que la respalda.',note:'La demo usa plantillas para que el resultado sea reproducible. No hay una llamada a un LLM generador.'},
  {name:'Aprobación y canal',input:'Propuesta, contacto del CRM y mensaje revisado.',process:'La persona aprueba. El servidor vuelve a comprobar el caso y vincula la aprobación al mensaje y destinatario.',output:'Simulación de WhatsApp o borrador de correo, según el canal autorizado.',note:'El modo de clase no envía mensajes externos. La conexión al gateway exige activación explícita.'}
];
function table(headers,rows) {return `<table class="lesson-table"><thead><tr>${headers.map(t=>`<th>${h(t)}</th>`).join('')}</tr></thead><tbody>${rows.map(row=>`<tr>${row.map(t=>`<td>${h(t)}</td>`).join('')}</tr>`).join('')}</tbody></table>`;}
function advisorInput() {return {documentType:$('documentType').value,documentNumber:$('documentNumber').value,query:$('query').value,actor:$('actor').value};}
function visual(index) {
  const ready=Boolean(current&&!stale);
  if(index===0){
    const input=ready?current.query:advisorInput();
    const profile=ready?current.actor:$('actor').selectedOptions[0].textContent;
    return `<div class="lesson-prompt"><small>CONSULTA DEL ASESOR</small><h3>${h(input.documentType)} ${h(input.documentNumber)}</h3><p>${h(input.query)}</p><small>${h(profile)} · perfil simulado</small></div>`;
  }
  if(!ready) return `<div class="lesson-prompt"><b>${h(stages[index].name)}</b><p>${pending?'La consulta se está procesando. Los resultados aparecerán al terminar.':'Ejecuta la pregunta del asesor para ver los datos de esta etapa.'}</p></div>`;
  const d=current, r=d.ragPipeline;
  switch(index) {
    case 1:return `<div class="source-stack"><span>Deuda: <b>${h(money(d.total))}</b></span><span>Historial: <b>${d.history.length} eventos</b></span><span>CRM: <b>${h(d.customer.preferredChannel)}</b></span></div>`;
    case 2:return `<div class="lesson-vector"><code>[${r.queryVector.slice(0,8).map(x=>Number(x).toFixed(4)).join(', ')}${r.queryVector.length>8?', …':''}]</code><p>${r.concepts.map(h).join(' · ')}</p><small>${d.prepared?'Cuatro valores ilustrativos precargados; no se genera un embedding en esta ejecución.':realRag?`${r.dimensionCount} dimensiones reales · primeros ocho valores`:'Cuatro dimensiones didácticas'}</small></div>`;
    case 3:return table(['Fragmento','Vector','Léxica','Fusión'],r.fused.slice(0,5).map(x=>[`${x.document_code} · ${x.section}`,x.vectorRank||'—',x.lexicalRank||'—',x.fusionRank]));
    case 4:return table(['Fuente','Antes','Después'],d.rag.map(x=>[`${x.document_code} · ${x.section}`,x.fusionRank,x.rerankPosition]));
    case 5:if(d.prepared)return `<div class="answer-demo"><span>SIMULACIÓN: PREPARAR PARA REVISIÓN</span><b>${h(d.decision.label)}</b><p>${h(d.decision.reason)}</p></div>`;return `<div class="answer-demo"><span>${d.decision.canApprove?'SÍ: PREPARAR PARA REVISIÓN':'NO: BLOQUEAR LA ACCIÓN'}</span><b>${h(d.decision.label)}</b><p>${h(d.decision.reason)}</p></div>`;
    case 6:return `<div class="answer-demo"><span>${d.prepared?'RESPUESTA PRECARGADA PARA CLASE':realRag?'RESPUESTA DEL LLM LOCAL':'RESPUESTA POR PLANTILLA'}</span><p>${h(d.answer)}</p></div>`;
    case 7:if(d.prepared)return `<div class="answer-demo"><span>REVISIÓN HUMANA · SIMULACIÓN</span><b>Canal del caso: ${h(d.customer.preferredChannel)}</b><p>El asesor revisaría el saldo, la política y el borrador antes de aprobar. Esta demostración termina aquí, sin registrar aprobaciones ni enviar mensajes.</p></div>`;return `<div class="answer-demo"><span>${approval?'APROBACIÓN REGISTRADA':d.decision.canApprove?'REVISIÓN HUMANA PENDIENTE':'ACCIÓN BLOQUEADA'}</span><b>${h(d.customer.preferredChannel)}</b><p>${approval?'Mensaje y destinatario vinculados a esta aprobación.':d.decision.canApprove?'Revisa y aprueba la propuesta en el panel inferior.':'El flujo termina en pausa o revisión humana, sin preparar un envío.'}</p></div>`;
  }
}
function renderStage(index) {
  stageIndex=Math.max(0,Math.min(stages.length-1,index));const stage=stages[stageIndex];
  $('pipelineCounter').textContent=`ETAPA ${stageIndex+1} DE ${stages.length}`;
  $('pipelineTitle').textContent=stage.name;$('pipelineDescription').textContent=stage.process;
  $('pipelineInput').textContent=stage.input;$('pipelineProcess').textContent=stage.process;$('pipelineOutput').textContent=stage.output;$('pipelineRisk').textContent=stage.note;
  const ready=Boolean(current&&!stale);
  $('pipelineQuestion').textContent=$('query').value.trim()||'Escribe la pregunta en Consulta del asesor.';
  $('pipelineQuestionStatus').textContent=pending?'Cargando el recorrido preparado…':ready&&current.prepared?'Recorrido precargado listo. Esta pregunta acompaña los ocho pasos.':ready?'Consulta completada. Esta pregunta corresponde a los resultados del recorrido.':stale?'Vuelve a mostrar el recorrido preparado.':'Pregunta predeterminada. Pulsa Mostrar recorrido para ver las respuestas al instante.';
  $('pipelineArtifact').innerHTML=visual(stageIndex);$('pipelineEvidence').textContent=ready&&current.prepared?`Caso ${current.query.documentNumber} · simulación precargada`:ready?`Caso ${current.query.documentNumber} · ${current.mode==='fixtures'?'datos incorporados':current.mode==='sqlite'?'SQLite + RAG':'PostgreSQL'}`:'La pregunta del asesor acompaña las ocho etapas.';
  $('pipelineMetric').textContent=ready&&current.prepared?'Sin llamadas al modelo · sin envíos':ready?(current.decision.canApprove?'Propuesta pendiente de aprobación':'Contacto bloqueado'):'';
  $('pipelinePrev').disabled=stageIndex===0;$('pipelineNext').disabled=stageIndex===stages.length-1;
  [...$('pipelineSteps').children].forEach((button,i)=>{button.classList.toggle('active',i===stageIndex);if(i===stageIndex)button.setAttribute('aria-current','step');else button.removeAttribute('aria-current');});
  const view=$('pipelineArtifact');if(!matchMedia('(prefers-reduced-motion: reduce)').matches)view.animate([{transform:'translateX(12px)'},{transform:'translateX(0)'}],{duration:220});
}
function invalidateApproval() {approval=null;$('reviewConfirmed').checked=false;$('approvalStatus').textContent=current?.decision.canApprove?'Revisión pendiente.':'Acción bloqueada.';updateActions();}
function updateActions() {
  const eligible=Boolean(current?.decision.canApprove&&!stale);
  $('approveButton').disabled=!eligible||!$('reviewConfirmed').checked;
  $('whatsappButton').disabled=!approval||stale||approval.channel!=='WHATSAPP';
  $('emailButton').disabled=!approval||stale||approval.channel!=='EMAIL';
}
function render(data) {
  current=data;stale=false;approval=null;$('empty').hidden=true;$('dashboard').hidden=false;$('error').textContent='';
  $('currentCase').textContent=`Caso ${data.query.documentType} ${data.query.documentNumber} · ${data.customer.fullName}`;
  $('traces').innerHTML=data.traces.map(x=>`<div class="trace"><b>${h(x.agent)}</b><br><span class="muted">${h(x.source)}</span><p>${h(x.result)}</p></div>`).join('');
  $('customer').innerHTML=`<div class="item"><b>${h(data.customer.fullName)}</b><p>Canal autorizado en CRM: ${h(data.customer.preferredChannel)}</p></div>`;
  $('debts').innerHTML=data.overdue.map(x=>`<div class="item"><b>${h(x.account_code)}</b> · ${h(x.days_overdue)} días<br>Saldo: ${h(money(x.outstanding_amount))}</div>`).join('')||'<p>Sin deuda vencida.</p>';
  $('history').innerHTML=data.history.map(x=>`<div class="item"><b>${h(x.event_type)} · ${h(x.status)}</b><p>${h(x.details||'')}</p></div>`).join('')||'<p>Sin eventos registrados.</p>';
  $('queryTransform').innerHTML=`<p><b>Consulta de recuperación:</b> ${h(data.ragPipeline.retrievalText)}</p><p class="note">Incluye las señales operativas del caso. ${h(data.ragPipeline.lexicalMethod)}.</p>`;
  $('rag').innerHTML=data.rag.map(x=>`<details class="item"><summary><b>${h(x.document_code)} ${h(x.version)}</b> · ${h(x.section)}</summary><p>${h(x.content)}</p><p class="note">${data.prepared?'Pasaje del guion precargado. Las posiciones del recorrido son ilustrativas.':`Permiso ${h(x.access_role)} · documento activo · similitud ${Number(x.similarity).toFixed(3)} · RRF ${Number(x.fusionScore).toFixed(4)} · ${realRag?'contexto documental verificado':'re-ranking didáctico '+x.rerankScore}`}</p><p class="note">${h(x.rerankReason)}</p></details>`).join('')||'<p>Sin pasajes autorizados.</p>';
  $('decision').innerHTML=`<div class="decision ${data.decision.canApprove?'':'blocked'}"><b>${h(data.decision.label)}</b><p>${h(data.decision.reason)}</p></div>`;
  $('answer').textContent=data.answer;
  const links={'POL-COB-04':'pol-cob-04','POL-PAG-02':'pol-pag-02','MAN-ATN-02':'man-atn-02','POL-PRO-03':'pol-pro-03'};
  $('citations').innerHTML=data.citations.map(c=>`<a href="${h(c.url||'/documentos/'+links[c.code]+'.html')}" target="_blank" rel="noopener">${c.id?'['+c.id+'] ':''}${h(c.code)} ${h(c.version)} · ${h(c.section)}</a>`).join(' ');
  $('reminder').hidden=!data.decision.canApprove;$('email').value=data.customer.email||'';$('whatsapp').value=data.customer.whatsapp||'';$('message').value=data.reminder;
  $('channel').value=data.customer.preferredChannel;$('authorizedContact').textContent=`Contacto del CRM: ${data.customer.preferredChannel==='WHATSAPP'?data.customer.whatsapp:data.customer.email}`;
  $('sendResult').textContent='';invalidateApproval();renderStage(0);
}
async function post(url,body) {const response=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const data=await response.json();if(!response.ok)throw Error(data.error||'No se pudo completar la acción.');return data;}
function showResult(text,error=false) {$('sendResult').className=`send-result ${error?'error':'success'}`;$('sendResult').textContent=text;}
$('searchForm').addEventListener('submit',async event=>{
  event.preventDefault();
  const button=$('searchButton'),input=advisorInput(),revision=inputRevision;
  button.disabled=true;button.textContent='Cargando recorrido…';pending=true;stale=true;invalidateApproval();$('error').textContent='';
  $('dashboard').hidden=true;$('empty').hidden=false;$('empty').textContent='Cargando los datos y respuestas del guion preparado…';renderStage(0);
  try {
    const response=await fetch('/advisor-prepared.json');
    if(!response.ok)throw Error('No se pudo cargar el recorrido preparado.');
    const data=await response.json();
    if(input.query!==data.query.query||input.documentNumber!==data.query.documentNumber||input.documentType!==data.query.documentType||input.actor!==data.query.actor)throw Error('Este recorrido preparado corresponde únicamente a la pregunta y al cliente predeterminados.');
    if(revision!==inputRevision){$('currentCase').textContent='Consulta modificada. Ejecuta de nuevo para actualizar la decisión.';$('empty').textContent='La pregunta cambió durante la consulta. Ejecuta de nuevo para actualizar los resultados.';return;}
    render(data);
  }
  catch(error){$('error').textContent=error.message;$('currentCase').textContent='La consulta no se completó. Ejecútala de nuevo antes de actuar.';$('empty').textContent='La consulta no se completó. Revisa el aviso y vuelve a ejecutar la pregunta.';}
  finally {pending=false;button.disabled=false;button.textContent='Mostrar recorrido';renderStage(stageIndex);}
});
for(const input of [$('documentType'),$('documentNumber'),$('query'),$('actor')])input.addEventListener('input',()=>{
  inputRevision++;stale=true;invalidateApproval();$('dashboard').hidden=true;$('empty').hidden=false;
  $('empty').textContent='Consulta modificada. Ejecuta la pregunta para actualizar los resultados.';
  $('currentCase').textContent='Consulta modificada. Ejecuta de nuevo para actualizar la decisión.';renderStage(stageIndex);
});
for(const input of [$('message'),$('email'),$('whatsapp'),$('channel')])input.addEventListener('input',()=>{invalidateApproval();$('sendResult').textContent='';});
$('reviewConfirmed').addEventListener('change',()=>{if(!$('reviewConfirmed').checked)approval=null;updateActions();});
$('approveButton').addEventListener('click',async()=>{
  const button=$('approveButton');button.disabled=true;
  try {
    if(!current||stale)throw Error('Ejecuta nuevamente el caso.');
    const channel=$('channel').value,to=(channel==='WHATSAPP'?$('whatsapp').value.replace(/\D/g,''):$('email').value.trim().toLowerCase());
    approval=await post('/api/cobranza/approve',{executionId:current.executionId,confirmed:$('reviewConfirmed').checked,channel,to,text:$('message').value});
    $('approvalStatus').textContent='Aprobación registrada para este mensaje y contacto.';showResult('La aprobación no ejecuta el envío.');renderStage(7);
  }catch(error){approval=null;showResult(error.message,true);}finally{updateActions();}
});
async function dispatch(channel) {
  if(!approval||!current||stale)return;
  const approved=approval;approval=null;updateActions();
  try {
    const data=await post(channel==='WHATSAPP'?'/api/reminders/whatsapp':'/api/reminders/email-draft',{executionId:current.executionId,approvalId:approved.approvalId,to:approved.to,text:$('message').value});
    if(channel==='EMAIL') {showResult('Borrador aprobado. Se abrirá tu aplicación de correo; no se envió un correo automáticamente.');location.href=data.mailto;}
    else showResult(data.simulated?'Simulación completada. No se envió ningún WhatsApp externo.':'El gateway aceptó la solicitud. Revise su resultado de entrega.');
    $('approvalStatus').textContent='Acción procesada. Otra acción requiere una nueva aprobación.';
  }catch(error){showResult(error.message,true);$('approvalStatus').textContent='La acción no se completó. Revise el resultado antes de volver a aprobar.';}
  finally{$('reviewConfirmed').checked=false;updateActions();renderStage(7);}
}
$('whatsappButton').addEventListener('click',()=>dispatch('WHATSAPP'));$('emailButton').addEventListener('click',()=>dispatch('EMAIL'));
$('pipelineSteps').innerHTML=stages.map((s,i)=>`<button type="button" class="pipeline-step" data-stage="${i}"><span>${String(i+1).padStart(2,'0')}</span>${h(s.name)}</button>`).join('');
$('pipelineSteps').addEventListener('click',event=>{const button=event.target.closest('[data-stage]');if(button)renderStage(Number(button.dataset.stage));});
$('pipelinePrev').onclick=()=>renderStage(stageIndex-1);$('pipelineNext').onclick=()=>renderStage(stageIndex+1);$('pipelineReset').onclick=()=>renderStage(0);
function configurePrepared(){
  const descriptions=[
    ['Muestra la pregunta predeterminada y el perfil del asesor.','Pregunta fija del guion, sin ejecutar consultas.'],
    ['Muestra el saldo de S/ 1,850, 18 días de atraso y el pago anterior aplicado.','Datos sintéticos precargados del cliente de ejemplo.'],
    ['Muestra cuatro valores para ilustrar la representación vectorial de una pregunta.','Vector inventado para clase. No se invoca al modelo de embeddings.'],
    ['Muestra dos órdenes de ejemplo y su lista fusionada de fragmentos.','Posiciones precargadas e ilustrativas. Esta ejecución no realiza búsquedas.'],
    ['Muestra cómo la regla de gestión temprana pasa al primer lugar del contexto.','Orden preparado para explicar la selección. No se consulta al modelo de reranking.'],
    ['Muestra la decisión preparada: borrador informativo para revisión humana.','No hay pago pendiente ni otra condición de pausa en este caso sintético.'],
    ['Muestra la explicación preparada y sus fuentes documentales.','Respuesta redactada para clase. No se llama al modelo generador.'],
    ['Explica la revisión humana y el canal del cliente antes de cualquier envío.','Simulación finalizada. No registra aprobaciones ni envía mensajes.']
  ];
  const outputs=['Pregunta fija y cliente del guion preparados para el recorrido.','Saldo, historial y canal del cliente de ejemplo.','Vector ilustrativo de cuatro valores, listo para explicar la búsqueda.','Lista precargada de fragmentos con sus posiciones de ejemplo.','Contexto del guion con documento, versión y sección.','Borrador para revisión humana, sin habilitar acciones reales.','Respuesta precargada con sus fuentes.','Revisión y canal explicados, sin aprobación ni envío reales.'];
  descriptions.forEach(([process,note],i)=>Object.assign(stages[i],{process,note,output:outputs[i]}));
}
configurePrepared();
renderStage(0);updateActions();
function configureLocal(status){
  realRag=true;
  document.querySelector('.library-link').href='#localRagPanel';document.querySelector('.library-link').textContent='Ver los documentos Word realmente indexados';
  stages[2].process=`${status.embeddingModel} genera un embedding real de ${status.dimensions||'…'} dimensiones para la consulta.`;stages[2].note='El mismo modelo genera los vectores de los documentos y las preguntas. Los vectores se conservan en SQLite.';
  stages[3].process='Busca por similitud coseno y BM25 de SQLite FTS5, aplica filtros y fusiona las listas con RRF.';stages[3].note='La búsqueda usa los textos extraídos de los Word y sus embeddings reales.';
  stages[4].process=status.generationProvider==='openai'?'La fusión RRF selecciona hasta seis pasajes sin otra llamada al LLM.':`${status.generationModel} reordena los candidatos y selecciona el contexto.`;stages[4].note='El orden no equivale a una probabilidad de verdad.';
  stages[6].process=`${status.generationModel} genera la respuesta a partir de los pasajes recuperados.`;stages[6].note='La aplicación valida que las citas pertenezcan al contexto. La revisión humana comprueba fidelidad y completitud.';
  stages[1].note='Los datos sintéticos de clientes, obligaciones e historial están persistidos y se consultan en SQLite.';
  $('implementationNote').textContent=`RAG híbrido: archivos Word, embeddings ${status.embeddingModel}, recuperación híbrida en SQLite y generación con ${status.generationModel} mediante ${status.generationProvider==='openai'?'OpenAI/n8n':'Ollama'}. La orquestación usa funciones del programa. Los datos de negocio y las políticas de la clase son sintéticos.`;
  $('implementationNote').textContent+=' El recorrido de ocho etapas usa respuestas precargadas y se muestra al instante. La consulta libre utiliza el proveedor configurado. Ground Truth con jueces LLM puede consumir llamadas adicionales; no se ejecuta automáticamente.';
  configurePrepared();renderStage(stageIndex);
}
window.addEventListener('rag:status',event=>configureLocal(event.detail));
fetch('/api/health').then(async response=>{const data=await response.json();if(!response.ok)throw Error(data.error);$('dbStatus').textContent=data.database==='fixtures'?'Datos de clase incorporados · sin PostgreSQL':data.database==='sqlite'?'SQLite local · datos de clase':'PostgreSQL + pgvector conectado';$('dbStatus').className='status ok';$('waStatus').textContent=data.deliveryMode==='gateway'?'Gateway de WhatsApp habilitado':'Envío simulado · sin mensajes externos';if(data.ragMode==='local')configureLocal(data.rag);else $('implementationNote').textContent=data.implementation;}).catch(error=>{$('dbStatus').textContent='Base no disponible';$('dbStatus').className='status bad';$('error').textContent=error.message;});
