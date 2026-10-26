"""Verifica distribución y pruebas locales sin invocar modelos o APIs de pago."""
from pathlib import Path
import argparse,json,re,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--python',default=str(ROOT/'demo/.venv/bin/python'));p.add_argument('--node',default='node');args=p.parse_args()
for file in ROOT.rglob('*'):
    rel=file.relative_to(ROOT)
    if any(x in {'.git','.venv','node_modules','data','__pycache__'} for x in rel.parts) or not file.is_file():continue
    if file.suffix in {'.py','.md','.json','.jsonl','.toml','.yaml','.yml','.js','.mjs','.html','.sql','.txt'}:
        text=file.read_text()
        if re.search(r'sk-(?:proj-)?[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{25,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',text):raise SystemExit(f'Posible secreto: {rel}')
for file in (ROOT/'demo/n8n').glob('*.json'):
    workflow=json.loads(file.read_text())
    assert not workflow.get('active') and not workflow.get('pinData'),file
    assert all(not node.get('credentials') for node in workflow['nodes']),file
    for node in workflow['nodes']:
        for header in node.get('parameters',{}).get('headerParameters',{}).get('parameters',[]):
            assert not (header.get('name','').lower()=='authorization' and header.get('value','').startswith('Bearer ')),file
assert not any('/Users/' in file.read_text() for file in (ROOT/'demo/config').glob('*.json'))
for line in (ROOT/'evals/casos.jsonl').read_text().splitlines():json.loads(line)
# Bloqueo de conexiones TCP en todo el proceso unittest: incluso un mock ausente no puede usar una API.
runner="""import socket,unittest,sys

def deny(*args,**kwargs):raise AssertionError('Red deshabilitada en pruebas Python; utiliza un mock')
socket.socket.connect=deny
suite=unittest.defaultTestLoader.discover('demo/tests')
result=unittest.TextTestRunner(verbosity=1).run(suite)
sys.exit(not result.wasSuccessful())
"""
print('Distribución revisada. Ejecutando Python con conexiones de red bloqueadas.',flush=True)
subprocess.run([args.python,'-c',runner],cwd=ROOT,check=True)
print('Ejecutando pruebas del RAG local con modelos simulados.',flush=True)
subprocess.run([args.node,'--test'],cwd=ROOT/'rag/03_Demo_Cobranza',check=True)
print('Verificación aprobada. No se invocó OpenAI, Codex ni Claude; no se envió correo.',flush=True)
