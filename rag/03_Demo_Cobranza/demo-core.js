export const dimensions = ['cobranza', 'pagos', 'atención', 'promesas'];
export const normalize = text => String(text).toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9\s]/g, ' ').replace(/\s+/g, ' ').trim();
export const policyCodes = text => [...new Set(String(text).toUpperCase().match(/\b(?:POL|MAN|GUI)-[A-Z]{2,6}-\d{2}\b/g) || [])];

export function transformQuery(text) {
  const normalized = normalize(text), tokens = [...new Set(normalized.split(' ').filter(x => x.length > 2))];
  const concepts = [], vector = [0.08, 0.08, 0.08, 0.08];
  const add = (name, i) => { concepts.push(name); vector[i] += 0.9; };
  if (/atras|venc|deuda|cobran|saldo/.test(normalized)) add('deuda vencida', 0);
  if (/pago|deposit|transfer|concili|comprobante/.test(normalized)) add('pago y conciliación', 1);
  if (/especial|dificultad|reclamo|vulnerab|humana/.test(normalized)) add('atención especial', 2);
  if (/promesa|compromiso|incumpl|refinancia/.test(normalized)) add('promesas y negociación', 3);
  if (!concepts.length) { concepts.push('cobranza general'); vector[0] += 0.65; }
  const magnitude = Math.hypot(...vector);
  return { raw: text, normalized, tokens: tokens.slice(0, 30), concepts, queryVector: vector.map(v => Number((v / magnitude).toFixed(4))) };
}

export function caseRule(customer, overdue, history) {
  if (customer.special_attention) return { code: 'HUMAN_ATTENTION', policy: 'MAN-ATN-02', label: 'Derivar a atención humana', reason: 'El CRM marca el caso para atención especial.' };
  if (history.some(x => x.status === 'PENDING_RECONCILIATION')) return { code: 'PAUSE_AND_RECONCILE', policy: 'POL-PAG-02', label: 'Pausar contacto y conciliar', reason: 'El historial registra un pago pendiente de conciliación.' };
  if (history.some(x => x.status === 'BROKEN')) return { code: 'HUMAN_REVIEW', policy: 'POL-PRO-03', label: 'Revisar la promesa incumplida', reason: 'Se necesita revisión humana del historial antes de proponer otra alternativa.' };
  if (!overdue.length) return { code: 'NO_OVERDUE', policy: null, label: 'No preparar un recordatorio', reason: 'Las fuentes operativas no muestran deuda vencida.' };
  if (overdue.some(x => Number(x.days_overdue) > 30)) return { code: 'HUMAN_REVIEW', policy: 'POL-COB-04', label: 'Revisar el caso fuera de alcance', reason: 'La política docente de gestión temprana cubre hasta 30 días; este caso requiere revisión.' };
  return { code: 'READY_FOR_REVIEW', policy: 'POL-COB-04', label: 'Propuesta lista para revisión', reason: 'Existe deuda vencida dentro del alcance de la política y no se detectó una condición de pausa.' };
}

export function fuseAndRerank(vectorRows, lexicalRows, text, requiredCode, explicitCodes = []) {
  const candidates = new Map();
  for (const [route, rows] of [['vector', vectorRows], ['lexical', lexicalRows]]) rows.forEach((row, i) => {
    const item = candidates.get(row.id) || { ...row, vectorRank: null, lexicalRank: null, fusionScore: 0 };
    item[route + 'Rank'] = i + 1;
    item.fusionScore += 1 / (60 + i + 1);
    if (route === 'lexical') item.lexicalScore = Number(row.lexical_score || 0);
    candidates.set(row.id, item);
  });
  const fused = [...candidates.values()].sort((a, b) => b.fusionScore - a.fusionScore || a.id - b.id).map((x, i) => ({ ...x, fusionRank: i + 1 }));
  const terms = transformQuery(text).tokens;
  const reranked = fused.map(row => {
    const haystack = normalize(`${row.document_code} ${row.section} ${row.title} ${row.content}`);
    const overlap = terms.filter(t => haystack.includes(t)).length / Math.max(terms.length, 1);
    const ruleMatch = row.document_code === requiredCode;
    const explicitMatch = explicitCodes.includes(row.document_code);
    return { ...row, rerankScore: Number((overlap + (ruleMatch ? 2 : 0) + (explicitMatch ? 1 : 0)).toFixed(4)), rerankReason: ruleMatch ? 'Regla vinculada al estado operativo del caso' : explicitMatch ? 'Documento solicitado por su código' : 'Coincidencia de términos de la consulta' };
  }).sort((a, b) => b.rerankScore - a.rerankScore || a.fusionRank - b.fusionRank);
  return { fused, reranked: reranked.map((row, i) => ({ ...row, rerankPosition: i + 1 })) };
}

export function decide(rule, context, explicitCodes = []) {
  const missing = explicitCodes.filter(code => !context.some(x => x.document_code === code));
  if (missing.length || (rule.policy && !context.some(x => x.document_code === rule.policy))) return {
    code: 'INSUFFICIENT_EVIDENCE', label: 'Pausar y escalar por falta de evidencia',
    reason: missing.length ? `No hay evidencia autorizada y vigente para ${missing.join(', ')}.` : `No se recuperó la política requerida ${rule.policy}.`, canApprove: false
  };
  return { ...rule, canApprove: rule.code === 'READY_FOR_REVIEW' };
}

export function evidenceCitation(row) {
  return { code: row.document_code, version: row.version, section: row.section, content: row.content, title: row.title };
}

export async function analyze(repository, input) {
  const started = Date.now();
  const customer = await repository.customer(input.documentType, input.documentNumber);
  if (!customer) { const error = new Error('No se encontró el identificador en los datos sintéticos.'); error.status = 404; throw error; }
  const [obligations, history] = await Promise.all([repository.obligations(customer.id), repository.history(customer.id)]);
  const overdue = obligations.filter(x => x.status === 'OVERDUE' && Number(x.outstanding_amount) > 0);
  const rule = caseRule(customer, overdue, history);
  const explicitCodes = policyCodes(input.query);
  const operationalSignal = rule.policy ? ` ${rule.policy} ${rule.reason}` : '';
  const transformed = transformQuery(input.query + operationalSignal);
  const routes = await repository.candidates(transformed, input.roles, explicitCodes);
  const { fused, reranked } = fuseAndRerank(routes.vector, routes.lexical, transformed.raw, rule.policy, explicitCodes);
  const selected = reranked.slice(0, 4);
  const decision = decide(rule, selected, explicitCodes);
  const citations = decision.code === 'INSUFFICIENT_EVIDENCE' ? [] : selected.filter(x => x.document_code === rule.policy).map(evidenceCitation);
  const total = overdue.reduce((sum, x) => sum + Number(x.outstanding_amount), 0);
  const citationText = citations.map(c => `${c.code} ${c.version}, ${c.section}`).join('; ');
  const answer = `${decision.label}. ${decision.reason}${citationText ? ` Fuente: ${citationText}.` : ''}`;
  return {
    query: input, customer: { id: customer.id, fullName: customer.full_name, email: customer.email, whatsapp: customer.whatsapp, preferredChannel: customer.preferred_channel, specialAttention: customer.special_attention },
    overdue, history, total, decision, citations, answer,
    ragPipeline: { ...transformed, raw: input.query, retrievalText: transformed.raw, model: 'semantic-demo-4d-v1 · reglas didácticas', dimensions, explicitCodes, lexicalMethod: routes.method, vectorCandidates: routes.vector, lexicalCandidates: routes.lexical, fused, reranked, selectedIds: selected.map(x => x.id) },
    rag: selected,
    reminder: decision.canApprove ? `Hola. Registra un saldo vencido de S/ ${total.toFixed(2)}. Si ya realizó un pago, repórtelo por el canal autorizado para su revisión. Comuníquese con nuestro equipo para consultar su cuenta. Demostración con datos sintéticos.` : '',
    mode: repository.mode, elapsedMs: Date.now() - started,
    traces: [
      { agent: 'Orquestador', source: 'Consulta del asesor', result: 'Separa datos operativos, consulta documental y controles de acción.' },
      { agent: 'Deuda', source: 'obligations', result: `${overdue.length} obligación(es) vencida(s), S/ ${total.toFixed(2)}.` },
      { agent: 'Historial', source: 'payment_history', result: `${history.length} evento(s), incluidos pagos y promesas.` },
      { agent: 'Cliente', source: 'customers / CRM', result: `Canal autorizado del caso: ${customer.preferred_channel}.` },
      { agent: 'RAG', source: repository.mode === 'fixtures' ? 'Corpus sintético incorporado' : 'policy_documents + pgvector', result: `${routes.vector.length} vectoriales + ${routes.lexical.length} léxicos; ${selected.length} pasajes seleccionados.` }
    ]
  };
}
