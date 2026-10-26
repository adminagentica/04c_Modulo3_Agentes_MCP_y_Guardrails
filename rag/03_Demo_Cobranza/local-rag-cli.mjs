import { LocalRag } from './local-rag.js';
const rag=new LocalRag();
try{
  console.log('Comprobando archivos y modelos locales…');
  const status=await rag.start(process.argv[2]==='ingest');
  console.log(JSON.stringify(status,null,2));
  if(process.argv[2]==='query'){
    const result=await rag.query(process.argv.slice(3).join(' ')||'¿Qué información debe contener una promesa de pago?');
    console.log(JSON.stringify({answer:result.answer,citations:result.citations,insufficientEvidence:result.insufficientEvidence,elapsedMs:result.elapsedMs,generation:result.generation},null,2));
  }
}catch(error){console.error(error.message);process.exitCode=1;}
finally{rag.close();}
