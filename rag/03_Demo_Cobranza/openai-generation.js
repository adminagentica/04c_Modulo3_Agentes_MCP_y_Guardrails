/** OpenAI se invoca solo desde n8n; este cliente no conoce la API key. */
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const root=path.dirname(fileURLToPath(import.meta.url));
export async function generateWithOpenAI(messages,schema,options={}){
 const endpoint=new URL(options.url||process.env.RAG_OPENAI_WEBHOOK||'http://127.0.0.1:5678/webhook/agentica-rag-generate');
 if(endpoint.protocol!=='http:'||!['127.0.0.1','localhost'].includes(endpoint.hostname)||endpoint.username||endpoint.password||endpoint.search||endpoint.hash)throw Error('El webhook RAG debe ser local y sin redirecciones.');
 const token=options.token||process.env.COBRANZA_TOKEN||(await fs.readFile(process.env.COBRANZA_GATEWAY_TOKEN_FILE||path.resolve(root,'../../demo/data/gateway.token'),'utf8').catch(()=>'' )).trim();
 if(token.length<24)throw Error('Configura el token interno del RAG hacia n8n; la API key de OpenAI permanece en n8n.');
 const started=Date.now();let response;
 try{response=await(options.fetch||fetch)(endpoint.href,{method:'POST',redirect:'error',signal:AbortSignal.timeout(110000),headers:{'Content-Type':'application/json',Authorization:'Bearer '+token},body:JSON.stringify({messages,schema})});}
 catch{throw Error('n8n no pudo generar la respuesta RAG; no se reintentó ni se cambió a un modelo local.');}
 const result=await response.json();
 if(!response.ok||result.error)throw Error('OpenAI/n8n no pudo generar la respuesta. Revisa la credencial y el saldo en n8n.');
 if(!result.content||typeof result.content!=='object'||Array.isArray(result.content)||typeof result.model!=='string')throw Error('Contrato de generación RAG inválido.');
 return{content:result.content,model:result.model,provider:'openai',durationMs:Date.now()-started,inputTokens:result.usage?.input_tokens,outputTokens:result.usage?.output_tokens,executionId:result.execution_id};
}
