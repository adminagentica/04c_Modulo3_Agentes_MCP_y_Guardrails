import { normalize } from './demo-core.js';

export function postgresRepository(pool) {
  const fields = `p.id,p.document_code,p.version,p.section,p.title,p.content,p.active,p.access_role,p.embedding::text AS document_embedding,1-(p.embedding <=> $1::vector) AS similarity`;
  const scope = `p.active=true AND p.access_role=ANY($2::text[]) AND COALESCE((to_jsonb(p)->>'valid_from')::date,DATE '1900-01-01')<=CURRENT_DATE AND COALESCE((to_jsonb(p)->>'valid_until')::date,DATE '9999-12-31')>=CURRENT_DATE`;
  return {
    mode: 'postgres',
    async customer(type, number) { return (await pool.query('SELECT * FROM customers WHERE document_type=$1 AND document_number=$2', [type, number])).rows[0]; },
    async obligations(id) { return (await pool.query(`SELECT *,GREATEST(CURRENT_DATE-due_date,0) AS days_overdue FROM obligations WHERE customer_id=$1 ORDER BY due_date`, [id])).rows; },
    async history(id) { return (await pool.query('SELECT * FROM payment_history WHERE customer_id=$1 ORDER BY event_date DESC', [id])).rows; },
    async candidates(query, roles, codes) {
      const vector = `[${query.queryVector.join(',')}]`;
      const words = query.tokens.join(' OR ') || 'cobranza';
      const text = `to_tsvector('spanish',concat_ws(' ',p.document_code,p.section,p.title,p.content))`;
      const tsquery = `websearch_to_tsquery('spanish',$3)`;
      const [v, l] = await Promise.all([
        pool.query(`SELECT ${fields} FROM policy_documents p WHERE ${scope} ORDER BY p.embedding <=> $1::vector,p.id LIMIT 8`, [vector, roles]),
        pool.query(`SELECT ${fields},ts_rank_cd(${text},${tsquery}) AS lexical_score FROM policy_documents p WHERE ${scope} AND (${text} @@ ${tsquery} OR p.document_code=ANY($4::text[])) ORDER BY (p.document_code=ANY($4::text[])) DESC,lexical_score DESC,p.id LIMIT 8`, [vector, roles, words, codes])
      ]);
      return { vector: v.rows, lexical: l.rows, method: 'Full-text PostgreSQL (ts_rank_cd), no BM25' };
    }
  };
}

export function fixtureRepository() {
  const customers = [
    { id: 1, document_type: 'DNI', document_number: '74851236', full_name: 'Cliente Demo Uno', email: 'cliente.demo@example.com', whatsapp: '51999900001', preferred_channel: 'WHATSAPP' },
    { id: 2, document_type: 'RUC', document_number: '20548796321', full_name: 'Comercial Demo SAC', email: 'pagos@comercialdemo.example', whatsapp: '51999900002', preferred_channel: 'EMAIL' },
    { id: 3, document_type: 'DNI', document_number: '40112233', full_name: 'Cliente Atención Especial', email: 'atencion@example.com', whatsapp: '51999900003', preferred_channel: 'EMAIL', special_attention: true },
    { id: 4, document_type: 'DNI', document_number: '71234567', full_name: 'Carlos Demo Salas', email: 'carlos.demo@example.com', whatsapp: '51999900006', preferred_channel: 'WHATSAPP' },
    { id: 5, document_type: 'RUC', document_number: '20601234567', full_name: 'Distribuidora Laboratorio SAC', email: 'cobranzas@laboratorio.example', whatsapp: '51999900005', preferred_channel: 'EMAIL' }
  ];
  const obligations = [[1,'CB-204',18,1850],[2,'CB-310',32,3200],[3,'CB-411',12,750],[4,'CB-714',65,600],[5,'CB-613',8,12500]].map(([customer_id,account_code,days_overdue,outstanding_amount])=>({ customer_id,account_code,days_overdue,outstanding_amount,status:'OVERDUE' }));
  const history = [
    { customer_id:1,event_type:'PAYMENT',status:'APPLIED',amount:900,details:'Pago anterior aplicado' },
    { customer_id:2,event_type:'PAYMENT',status:'PENDING_RECONCILIATION',amount:1600,details:'Pago informado, pendiente de conciliación' },
    { customer_id:2,event_type:'PROMISE',status:'BROKEN',amount:1200,details:'Promesa anterior incumplida' },
    { customer_id:3,event_type:'NOTE',status:'HUMAN_REVIEW',details:'Atención especial' },
    { customer_id:4,event_type:'PROMISE',status:'BROKEN',amount:500,details:'Compromiso vencido' }
  ];
  const policies = [
    ['POL-COB-04','v3','§5 Gestión temprana','Política de cobranza temprana','Para atrasos de hasta 30 días, el agente puede preparar una propuesta dentro de los rangos autorizados. La confirmación requiere un responsable humano.',[.95,.10,.05,.20]],
    ['POL-PAG-02','v4','§4 Conciliación','Política de aplicación de pagos','Cuando existe un pago pendiente de conciliación se debe pausar el contacto de cobranza y derivar el caso a Operaciones.',[.10,.95,.15,.05]],
    ['MAN-ATN-02','v2','§3 Atención especial','Manual de atención al cliente','Los casos marcados para atención especial requieren intervención humana y no deben continuar con negociación automatizada.',[.05,.15,.95,.10]],
    ['POL-PRO-03','v3','§7 Promesas incumplidas','Política de promesas de pago','Una promesa incumplida requiere revisar el historial antes de presentar una nueva alternativa.',[.20,.05,.10,.95]]
  ].map(([document_code,version,section,title,content,embedding],i)=>({ id:i+1,document_code,version,section,title,content,embedding,document_embedding:JSON.stringify(embedding),active:true,access_role:'COBRANZA' }));
  function eligible(p, roles) { const today=new Date().toISOString().slice(0,10);return p.active && roles.includes(p.access_role) && (!p.valid_from||p.valid_from<=today) && (!p.valid_until||p.valid_until>=today); }
  return {
    mode:'fixtures', policies, customers, events:history, debts:obligations,
    async customer(type,number){return customers.find(c=>c.document_type===type&&c.document_number===number);},
    async obligations(id){return obligations.filter(x=>x.customer_id===id);},
    async history(id){return history.filter(x=>x.customer_id===id);},
    async candidates(query,roles,codes){
      const rows=policies.filter(p=>eligible(p,roles)).map(p=>({ ...p,similarity:p.embedding.reduce((sum,v,i)=>sum+v*query.queryVector[i],0)/(Math.hypot(...p.embedding)*Math.hypot(...query.queryVector)) }));
      const vector=[...rows].sort((a,b)=>b.similarity-a.similarity||a.id-b.id).slice(0,8);
      const lexical=rows.map(p=>({ ...p,lexical_score:query.tokens.filter(t=>normalize(p.document_code+' '+p.title+' '+p.content).includes(t)).length+(codes.includes(p.document_code)?10:0) })).filter(p=>p.lexical_score>0).sort((a,b)=>b.lexical_score-a.lexical_score||a.id-b.id).slice(0,8);
      return {vector,lexical,method:'Coincidencias de palabras en datos incorporados (simulación de full-text)'};
    }
  };
}
