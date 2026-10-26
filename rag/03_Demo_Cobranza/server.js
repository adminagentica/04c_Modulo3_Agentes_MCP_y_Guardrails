import { createApp } from './app-server.js';
process.env.RAG_MODE ||= process.env.DEMO_DATA_MODE ? 'didactic' : 'local';
const port=Number(process.env.PORT||4173);
createApp().listen(port,'127.0.0.1',()=>console.log(`Demo de cobranza: http://localhost:${port}`));
