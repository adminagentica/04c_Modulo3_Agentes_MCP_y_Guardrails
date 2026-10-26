// Los nombres visibles explican los indicadores; las claves y los cálculos se conservan.
// El contenido del modelo se presenta con textContent, nunca como instrucciones o HTML.
(()=>{
const pct=value=>value==null?'No aplica':(value*100).toFixed(1)+' %';
function add(parent,tag,value,className){const node=document.createElement(tag);node.textContent=value;if(className)node.className=className;parent.append(node);return node;}
const groups=['Recuperación: encontrar la evidencia','Respuesta: usar y explicar la evidencia','Citas y falta de evidencia'];
function indicators(k){return [
  {key:'precisionAtK',name:'Precisión de recuperación',technical:`Precision@${k}`,group:0,
    question:'¿Cuánto de lo recuperado coincide con las fuentes esperadas?',
    formula:`Fragmentos de secciones etiquetadas encontrados ÷ ${k}. Las posiciones vacías cuentan como cero.`,
    example:`Si solo 1 de los ${k} fragmentos coincide con una sección esperada: 1 ÷ ${k} = ${pct(1/k)}.`,
    reading:'Más alto es mejor. Un fragmento sin etiqueta puede ser útil: esta demo mide coincidencia con las referencias, no toda la relevancia posible del corpus.'},
  {key:'recallAtK',name:'Cobertura',technical:`Recall@${k}`,group:0,
    question:'¿Encontramos todas las secciones que debíamos recuperar?',
    formula:`Secciones esperadas distintas encontradas entre los primeros ${k} fragmentos ÷ total de secciones esperadas.`,
    example:'Si la referencia exige 2 secciones y aparece 1: 1 ÷ 2 = 50 %. Repetir la misma sección no aumenta la cobertura.',
    reading:'Más alto es mejor. Una cobertura baja señala evidencia esperada que falta en el contexto. Se refiere a documentos recuperados, no a qué tan completa quedó la respuesta.'},
  {key:'hitAtK',name:'Acierto de recuperación',technical:`Hit@${k}`,group:0,
    question:'¿Apareció al menos una sección esperada?',
    formula:`Preguntas con al menos una sección esperada entre los primeros ${k} fragmentos ÷ preguntas evaluadas para recuperación.`,
    example:'Si 8 de 10 preguntas encuentran al menos una sección esperada: 8 ÷ 10 = 80 %. En un solo caso se muestra Sí o No.',
    reading:'Más alto es mejor. Encontrar una sección basta para acertar, aunque todavía falten otras. Por eso acierto y cobertura pueden tener valores diferentes.'},
  {key:'mrrAtK',name:'Posición de la evidencia',technical:`MRR@${k}`,group:0,score:true,
    question:'¿Qué tan pronto aparece la primera sección esperada?',
    formula:`En cada caso: 1 ÷ posición de la primera sección esperada dentro de los primeros ${k}. Si no aparece: 0. Después se promedian los casos.`,
    example:k===1?'Con K = 1 solo se revisa la primera posición. Si aciertan 2 de 3 casos: (1 + 1 + 0) ÷ 3 = 0.667.':'Primeras evidencias en posiciones 1, 2 y sin acierto: (1 + 0.5 + 0) ÷ 3 = 0.500.',
    reading:'Es una puntuación de 0 a 1, no un porcentaje. Cuanto más cerca de 1, antes aparece la evidencia. En el detalle de un caso se llama RR, sin promediar.'},
  {key:'fidelity',name:'Respaldo de la respuesta',technical:'Fidelidad al contexto',group:1,
    question:'¿Lo que afirma la respuesta está sustentado en los pasajes entregados al modelo?',
    formula:'Unidades de la respuesta respaldadas por el contexto ÷ unidades evaluadas de la respuesta.',
    example:'La respuesta tiene 3 frases evaluables. Dos tienen respaldo y una inventa una penalidad: 2 ÷ 3 = 66.7 %.',
    reading:'Más alto es mejor. Una respuesta puede tener respaldo y aun así omitir parte de lo solicitado. Las unidades siguen la rúbrica de la demo; una lista en una oración puede contar como una unidad. El juicio automático requiere revisión humana.'},
  {key:'completeness',name:'Respuesta completa',technical:'Completitud',group:1,
    question:'¿La respuesta cubre todos los puntos que exigía la referencia?',
    formula:'Requisitos de la respuesta esperada que sí se explican ÷ total de requisitos esperados.',
    example:'Se esperaba «pausar el contacto y derivar a Operaciones». La respuesta solo dice «pausar el contacto»: cubre 1 de 2 puntos, 50 %.',
    reading:'Más alto es mejor. Se revisa el texto de la respuesta obtenida: recuperar un documento que contiene el punto no significa que la respuesta lo haya explicado. Cubrir todos los puntos no compensa una afirmación inventada.'},
  {key:'correctAbstentionRate',name:'Reconoce que falta evidencia',technical:'Abstención correcta',group:2,
    question:'¿Evita inventar una respuesta cuando la referencia exige abstenerse?',
    formula:'Casos donde se abstuvo correctamente ÷ casos que debían abstenerse por falta de evidencia.',
    example:'De 10 casos sin evidencia suficiente, reconoce la limitación en 8: 8 ÷ 10 = 80 %.',
    reading:'Más alto es mejor. Solo se calcula sobre los casos que exigen abstención. Si no hay casos de ese tipo, se muestra No aplica. Un error técnico no cuenta como una abstención correcta.'},
  {key:'unjustifiedAbstentionRate',name:'Se abstiene sin necesidad',technical:'Abstención injustificada',group:2,lower:true,
    question:'¿Dice que no puede responder aunque el caso sí tenía evidencia esperada?',
    formula:'Abstenciones en casos con evidencia y sin error técnico ÷ casos con evidencia y sin error técnico.',
    example:'De 10 casos con evidencia que terminaron sin error, se abstiene en 2: 2 ÷ 10 = 20 %.',
    reading:'Menor es mejor. Aquí 0 % es el resultado deseable. Separa falta de evidencia de una respuesta que el RAG sí debía poder dar.'},
  {key:'citationHitRate',name:'Cita la fuente esperada',technical:'Acierto de cita',group:2,
    question:'¿La respuesta cita las secciones y versiones indicadas en la referencia?',
    formula:'Casos que citan todas las secciones esperadas ÷ casos que deberían responder con evidencia.',
    example:'De 10 casos con evidencia, 9 citan todas las fuentes esperadas: 9 ÷ 10 = 90 %.',
    reading:'Más alto es mejor. Una cita correcta identifica la fuente esperada; comprobar que respalda lo afirmado corresponde al indicador Respaldo de la respuesta.'}
];}
function explanation(parent,metric,heading='Ejemplo y cómo interpretarlo'){
  const detail=document.createElement('details');detail.className='gt-indicator-help';parent.append(detail);detail.dataset.indicatorKey=metric.key;
  add(detail,'summary',heading);add(detail,'p','Cálculo: '+metric.formula);add(detail,'p','Ejemplo ilustrativo: '+metric.example);add(detail,'p',metric.reading);
}
function renderGuide(){
  const parent=document.getElementById('gtIndicatorGuideContent');if(!parent)return;
  const k=Number(document.getElementById('gtK').value)||5;parent.replaceChildren();
  add(parent,'p',`K es la cantidad de fragmentos que revisamos por pregunta. Ahora has elegido ${k}. La demo evalúa el contexto final, después del reranking.`);
  const metrics=indicators(k);
  groups.forEach((group,index)=>{
    add(parent,'h4',group);
    for(const metric of metrics.filter(m=>m.group===index)){
      const item=document.createElement('div');parent.append(item);
      add(item,'p',metric.question);
      explanation(item,metric,`${metric.name} · ${metric.technical}`);
    }
  });
  add(parent,'p',`Ejemplo para distinguir precisión y cobertura: solo esperabas una sección y aparece entre ${k} posiciones. Precisión: 1 ÷ ${k} = ${pct(1/k)}. Cobertura: 1 ÷ 1 = 100 %. Encontraste todo lo esperado, pero las otras posiciones no coinciden con las etiquetas.`, 'gt-reading-example');
  add(parent,'p','Los ejemplos son ilustrativos. Los resultados guardados conservan la cantidad de fragmentos y las referencias de su propia ejecución. Ningún indicador aislado es una garantía de confiabilidad.');
}
window.renderGroundTruthMetrics=(run)=>{
  const root=document.getElementById('gtMetrics');
  const expanded=new Set([...root.querySelectorAll('details[data-indicator-key][open]')].map(node=>node.dataset.indicatorKey));
  root.replaceChildren();
  if(!run.metricsVersion){add(root,'p','Esta ejecución anterior no incluye los nuevos indicadores. Ejecuta los casos para calcularlos.');return;}
  const s=run.summary;
  add(root,'h3',`Indicadores: ${run.k} fragmentos revisados por pregunta`);
  add(root,'p',`${s.completed}/${s.total} casos procesados · ${s.errors} errores del RAG · calidad evaluada: ${s.qualityCases}/${s.qualityEligible} respuestas · ${s.judgeErrors} errores del evaluador.`);
  const metrics=indicators(run.k);
  groups.forEach((group,index)=>{
    add(root,'h4',group);
    const grid=document.createElement('div');grid.className='gt-metric-grid';root.append(grid);
    for(const metric of metrics.filter(m=>m.group===index)){
      const value=s[metric.key],card=document.createElement('div');card.className='gt-metric';grid.append(card);
      add(card,'b',metric.name);add(card,'small',metric.technical,'gt-technical-name');
      const pendingQuality=value==null&&['fidelity','completeness'].includes(metric.key)&&s.qualityEligible>0;
      const label=pendingQuality?(s.judgeErrors?'No disponible':'Pendiente'):metric.score?(value==null?'No aplica':value.toFixed(3)):pct(value);
      add(card,'strong',label);add(card,'p',metric.question);
      add(card,'small',metric.score?'Más cerca de 1 es mejor.':metric.lower?'Menor es mejor.':'Más alto es mejor.');
      explanation(card,metric);
      card.querySelector('details').open=expanded.has(metric.key);
    }
  });
  add(root,'p','Recuperación: se mide el contexto final después del reranking y se promedia por caso. Solo secciones etiquetadas como esperadas cuentan como relevantes; otras pueden ser útiles. Los casos que exigen abstención no entran en recuperación ni calidad de respuesta.');
  add(root,'p',`Respaldo y respuesta completa: evaluador ${run.evaluatorModel}, rúbrica inicial ${run.rubricVersion}. Cada caso conserva la versión usada y sus reintentos. Las respuestas binarias aisladas usan una regla explícita de comparación con la referencia. El resto usa un modelo local. Si el mismo modelo genera y evalúa, puede haber sesgo. Un fallo queda sin puntuación. Calibra los resultados con revisión humana; no hay un umbral universal de confiabilidad.`);
};
window.renderGroundTruthCaseMetrics=(r)=>{
  const wrap=document.createElement('div'),q=r.metrics?.quality,m=r.metrics?.retrieval;
  if(!r.metrics)return wrap;
  add(wrap,'h4','Indicadores del caso');
  if(m.applicable){
    const list=document.createElement('ul');wrap.append(list);
    add(list,'li',`Precisión de recuperación: ${pct(m.precisionAtK)}. De ${m.k} posiciones, ${m.relevantRetrieved} ${m.relevantRetrieved===1?'fragmento coincide':'fragmentos coinciden'} con las secciones esperadas.`);
    add(list,'li',`Cobertura: ${pct(m.recallAtK)}. Secciones esperadas recuperadas: ${m.foundExpectedSections}/${m.expectedSections}, sin contar repeticiones.`);
    add(list,'li',`Acierto de recuperación: ${m.hitAtK?'Sí':'No'}. ${m.hitAtK?'Apareció al menos una sección esperada.':'No apareció ninguna sección esperada.'}`);
    add(list,'li',`Posición de la evidencia: ${m.reciprocalRankAtK.toFixed(3)} (RR@${m.k}). ${m.firstRelevantRank?'La primera sección esperada aparece en la posición '+m.firstRelevantRank+'.':'No aparece evidencia esperada entre las posiciones revisadas.'}`);
    add(wrap,'p',`Fragmentos devueltos: ${m.returned} de ${m.k} posiciones revisadas. Las posiciones vacías cuentan como cero en precisión.`);
  }else add(wrap,'p','Recuperación: no aplica a este caso, porque la referencia exige reconocer la falta de evidencia.');
  if(q.state==='complete'){
    add(wrap,'p',`Respaldo de la respuesta: ${pct(q.fidelity)} (${q.claims.filter(c=>c.supported).length}/${q.claims.length} unidades respaldadas). Respuesta completa: ${pct(q.completeness)} (${q.requirements.filter(c=>c.covered).length}/${q.requirements.length} requisitos cubiertos). ${q.evaluationMethod==='binary_reference'?'Regla explícita para respuesta binaria.':'Juicio del modelo evaluador.'} Pendiente de revisión humana.`);
    const details=document.createElement('details');wrap.append(details);add(details,'summary','Ver cómo se evaluó la respuesta');
    add(details,'p',`Modelo: ${q.model} · rúbrica: ${q.rubricVersion}${q.sameModelAsGenerator?' · mismo modelo que genera la respuesta':''}.`);
    add(details,'h4','Qué afirmaciones tienen respaldo');
    for(const c of q.claims)add(details,'p',`${c.supported?'Respaldada':'Sin respaldo'}: ${c.text} · Texto de la respuesta: «${c.quote||'no registrado'}» · Evidencia: ${c.evidenceIds.map(id=>'['+id+']').join(', ')||'ninguna'} · ${c.reason}`);
    add(details,'h4','Qué puntos de la respuesta esperada se cubrieron');
    for(const c of q.requirements)add(details,'p',`${c.covered?'Cubierto':'Falta'}: ${c.text} · Texto de la respuesta: ${c.answerQuote?'«'+c.answerQuote+'»':'no encontrado'} · ${c.reason}`);
  }else add(wrap,'p',q.state==='pending'?'Evaluando el respaldo y la respuesta completa con el modelo local…':q.state==='error'?'No se pudo evaluar la calidad: '+q.error:q.reason);
  if(r.qualityAttempts?.length){
    const history=document.createElement('details');wrap.append(history);add(history,'summary',`Evaluaciones anteriores (${r.qualityAttempts.length})`);
    for(const a of r.qualityAttempts)add(history,'p',`Conservado: ${a.evaluatedAt||a.archivedAt}. ${a.quality.state==='error'?'Sin puntuación: '+a.quality.error:'Respaldo de la respuesta '+pct(a.quality.fidelity)+' · respuesta completa '+pct(a.quality.completeness)}.`);
  }
  return wrap;
};
const selector=document.getElementById('gtK');if(selector){selector.addEventListener('change',renderGuide);renderGuide();}
})();
