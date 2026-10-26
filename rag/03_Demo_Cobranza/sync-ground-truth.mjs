// Migración explícita autorizada para el ejercicio docente; no atribuye aprobación real.
import {LocalRag} from './local-rag.js';
import {GroundTruth} from './ground-truth.js';
const rag=new LocalRag();
try{
  await rag.start();const gt=new GroundTruth(rag);await gt.seed();
  for(const c of gt.cases()){
    const expectedSources=c.expectedSources.map(ref=>{
      const doc=rag.documents().find(d=>d.code===ref.code);
      if(!doc)throw Error(`No existe ${ref.code}`);
      const rows=rag.db.prepare('SELECT section,content FROM rag_chunks WHERE document_code=? AND version=?').all(ref.code,doc.version);
      if(!rows.some(r=>r.section.startsWith(ref.section+' ')&&r.content.includes(ref.quote)))throw Error(`La evidencia de ${c.id} cambió; requiere revisión del contenido.`);
      return{...ref,version:doc.version};
    });
    const changed=c.indexVersion!==rag.metadata().indexVersion||JSON.stringify(c.expectedSources)!==JSON.stringify(expectedSources);
    if(changed)gt.saveCase({...c,expectedSources,version:c.version+1,status:'draft',approvalMode:null,reviewer:null,reviewedAt:null,indexVersion:rag.metadata().indexVersion});
    const current=gt.getCase(c.id);
    if(current.status!=='validated'||current.approvalMode!=='simulated'){
      gt.validate(c.id,{confirmed:true,reviewer:'Experto docente simulado · aprobación para la clase',approvalMode:'simulated'});
    }
  }
  console.log(JSON.stringify({indexVersion:rag.metadata().indexVersion,cases:gt.cases().map(c=>({id:c.id,version:c.version,status:c.status,approvalMode:c.approvalMode,reviewer:c.reviewer,sources:c.expectedSources.map(r=>r.code+' '+r.version)}))},null,2));
}finally{rag.close();}
