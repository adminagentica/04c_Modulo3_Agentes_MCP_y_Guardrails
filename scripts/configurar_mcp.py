"""Registra la conexión de clase sin copiar secretos ni reemplazar conexiones existentes."""
from pathlib import Path
import argparse,json,subprocess,shutil
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();group=p.add_mutually_exclusive_group(required=True)
group.add_argument('--claude',action='store_true');group.add_argument('--codex',action='store_true');args=p.parse_args()
python=ROOT/'demo/.venv/bin/python';server=ROOT/'demo/src/mcp_server.py'
if not python.exists():raise SystemExit('Instala primero demo/.venv; consulta docs/02_INSTALACION.md.')
if args.claude:
    file=ROOT/'.mcp.json'
    config={'mcpServers':{'cobranza_local':{'command':str(python),'args':[str(server),'--profile','codex']}}}
    try:
        with file.open('x') as handle:json.dump(config,handle,indent=2);handle.write('\n')
    except FileExistsError:raise SystemExit('.mcp.json ya existe: revisa su contenido; no se sobrescribió.')
    print('Conexión creada en .mcp.json local. Reabre Claude Code y revisa el servidor.')
else:
    if not shutil.which('codex'):raise SystemExit('Instala primero el cliente Codex.')
    current=subprocess.run(['codex','mcp','get','cobranza_clase','--json'],capture_output=True,text=True)
    if current.returncode==0:raise SystemExit('cobranza_clase ya está registrado: revísalo antes de cambiarlo.')
    subprocess.run(['codex','mcp','add','cobranza_clase','--',str(python),str(server),'--profile','codex'],check=True)
    print('Conexión de clase registrada. No se ejecutó ningún modelo ni consulta funcional.')
