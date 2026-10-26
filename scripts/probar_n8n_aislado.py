"""Prueba n8n real aislado + supervisor + MCP real, RAG y LLM simulados. Cero OpenAI."""
from pathlib import Path
import argparse,json,os,secrets,shutil,sqlite3,subprocess,tempfile,time,uuid,urllib.request
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--python',default=str(ROOT/'demo/.venv/bin/python'));p.add_argument('--human-handoff',action='store_true');p.add_argument('--port',type=int,default=8793);p.add_argument('--broker-port',type=int,default=5694);args=p.parse_args()
n8n=shutil.which('n8n')
if not n8n:raise SystemExit('Instala n8n o agrega su ejecutable a PATH.')
with tempfile.TemporaryDirectory(prefix='agentica-n8n-simulado-') as tmp:
    folder=Path(tmp);token=secrets.token_urlsafe(32)
    env={**os.environ,'COBRANZA_TOKEN':token,'COBRANZA_DB':str(folder/'cases.sqlite'),
         'N8N_USER_FOLDER':str(folder/'n8n'),'N8N_RUNNERS_BROKER_PORT':str(args.broker_port),
         'N8N_DIAGNOSTICS_ENABLED':'false','N8N_LOG_LEVEL':'error','AGENTICA_DEMO_SRC':str(ROOT/'demo/src')}
    source=json.loads((ROOT/'demo/n8n/workflow.json').read_text())
    names={'App · Consulta recibida','Herramientas Python · Contexto','¿Requiere OpenAI?','OpenAI · Orquestador','Guardrails · Validar respuesta','App · Responder consulta','App · Solicitar aclaración'}
    nodes=[node for node in source['nodes'] if node['name'] in names]
    connections={key:value for key,value in source['connections'].items() if key in names}
    assert len(nodes)==7,'Revisar nombres del workflow: no ejecutar una selección incompleta'
    for node in nodes:
        node.pop('credentials',None)
        if node['name']=='App · Consulta recibida':node.update(type='n8n-nodes-base.manualTrigger',typeVersion=1,parameters={})
        if node['type']=='n8n-nodes-base.httpRequest':
            node['parameters']['url']=node['parameters']['url'].replace(':8790',':'+str(args.port))
            node['credentials']={'httpHeaderAuth':{'id':'mock-local-header','name':'Token efímero de prueba'}}
        if node['name']=='OpenAI · Orquestador':
            node.pop('credentials',None)
            code='const p=$("Herramientas Python · Contexto").first().json; return [{json:{statusCode:200,body:{model:"simulated-no-api-credit",output:[{content:[{type:"output_text",text:JSON.stringify({request_id:p.request_id,intro:"Consulta verificada contra las fuentes disponibles.",policy_answer:"Revisar las condiciones de contacto [3].",citation_ids:[3],state:"answered"})}]}],usage:{total_tokens:0}}}}];'
            node.update(type='n8n-nodes-base.code',typeVersion=2,parameters={'jsCode':'throw new Error("La derivación humana no debe invocar el modelo");' if args.human_handoff else code})
        if node['type']=='n8n-nodes-base.respondToWebhook':node.update(type='n8n-nodes-base.code',typeVersion=2,parameters={'jsCode':'return $input.all();'})
    ident=str(uuid.uuid4())
    fixture={'question':'Quiero hablar con un ejecutivo humano' if args.human_handoff else '¿Cuál es el saldo de 74851236 y puedo mandarle un recordatorio?','dni':'74851236','request_id':ident}
    nodes.append({'id':'fixture-web','name':'Consulta simulada','type':'n8n-nodes-base.code','typeVersion':2,'position':[0,0],'parameters':{'jsCode':'return [{json:{body:'+json.dumps(fixture)+'}}];'}})
    connections['App · Consulta recibida']={'main':[[{'node':'Consulta simulada','type':'main','index':0}]]}
    connections['Consulta simulada']={'main':[[{'node':'Herramientas Python · Contexto','type':'main','index':0}]]}
    assert all(node['parameters']['url'].startswith(f'http://127.0.0.1:{args.port}/') for node in nodes if node['type']=='n8n-nodes-base.httpRequest')
    assert not any('openAiApi' in node.get('credentials',{}) for node in nodes)
    workflow={'id':'agentica-simulation-only','name':'Prueba aislada: sin proveedor externo','active':False,'nodes':nodes,'connections':connections,'settings':{'executionOrder':'v1'}}
    wf=folder/'workflow.json';wf.write_text(json.dumps(workflow))
    cred=folder/'credentials.json';cred.write_text(json.dumps([{'id':'mock-local-header','name':'Token efímero de prueba','type':'httpHeaderAuth','data':{'name':'Authorization','value':'Bearer '+token}}]));cred.chmod(0o600)
    for cmd in [['import:credentials','--input='+str(cred)],['import:workflow','--input='+str(wf)]]:
        result=subprocess.run([n8n]+cmd,env=env,capture_output=True,text=True,timeout=90)
        if result.returncode:raise SystemExit('No se pudo preparar el n8n aislado; revisa la instalación local.')
    cred.unlink()
    (folder/'mock_gateway.py').write_text('''import os,sys
sys.path.insert(0,os.environ['AGENTICA_DEMO_SRC'])
import gateway,web_orchestration
web_orchestration.retrieve_passages=lambda question:{'index_version':'simulated-index','citations':[{'id':3,'code':'POL-COB-04','version':'v4','section':'§3','content':'Validar condiciones de contacto.','sourceHash':'a'*64}]}
web_orchestration.validate_bundle=lambda bundle:True
build_app=gateway.build_app
''')
    server=subprocess.Popen([args.python,'-m','uvicorn','mock_gateway:build_app','--factory','--app-dir',str(folder),'--host','127.0.0.1','--port',str(args.port)],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        for _ in range(30):
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{args.port}/',timeout=1):break
            except OSError:time.sleep(.1)
        else:raise RuntimeError('El servidor de prueba no inició; comprueba que el puerto esté libre.')
        result=subprocess.run([n8n,'execute','--id=agentica-simulation-only','--rawOutput'],env=env,capture_output=True,text=True,timeout=90)
        if result.returncode:raise RuntimeError('Falló el workflow aislado: '+result.stdout[-1200:].replace(token,'[omitido]'))
        if args.human_handoff:
            with sqlite3.connect(folder/'cases.sqlite') as db:
                db.row_factory=sqlite3.Row
                ticket=dict(db.execute('SELECT id,reason,status,case_id FROM human_handoffs WHERE request_id=?',(ident,)).fetchone())
                tools=[row[0] for row in db.execute("SELECT tool FROM team_events WHERE request_id=? AND status='completed'",(ident,))]
            assert ticket['status']=='pending' and ticket['reason']=='solicitud_explicita'
            assert 'derivar_a_humano' in tools
            (ROOT/'examples').mkdir(exist_ok=True)
            (ROOT/'examples/derivacion-humana-simulada.json').write_text(json.dumps({'verification':'n8n real aislado; solicitud explícita sin LLM ni envío','openai_calls':0,'emails_sent':0,'handoff':ticket,'tools':tools},ensure_ascii=False,indent=2)+'\n')
            print('n8n → supervisor → MCP → bandeja humana: APROBADO. LLM no invocado; correos: 0.')
        else:
            with sqlite3.connect(folder/'cases.sqlite') as db:
                row=db.execute('SELECT state,result FROM web_chat_runs WHERE id=?',(ident,)).fetchone()
            assert row and row[0]=='answered','La respuesta no completó la revisión'
            output=json.loads(row[1]);assert '1500.00' in output['answer'] and output['model']=='simulated-no-api-credit'
            assert {event['agent_id'] for event in output['agent_trace']}=={'orquestador','analista_saldo','analista_elegibilidad','rag_politicas','redactor_respuesta','revisor_respuesta'}
            assert output['mcp_transport']=='sdk_in_memory' and not output['email_sent']
            (ROOT/'examples').mkdir(exist_ok=True)
            (ROOT/'examples/traza-orquestacion-simulada.json').write_text(json.dumps({'verification':'n8n real aislado; MCP real; RAG y LLM simulados','openai_calls':0,'emails_sent':0,'result':output},ensure_ascii=False,indent=2)+'\n')
            print('n8n → supervisor → subagentes → MCP → revisión → memoria: APROBADO. OpenAI: 0 llamadas; correos: 0.')
    finally:
        server.terminate();server.wait(timeout=8)
