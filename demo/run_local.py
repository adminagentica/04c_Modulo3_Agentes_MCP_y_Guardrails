"""Inicia únicamente el gateway Python; RAG y n8n se ejecutan por separado."""
from pathlib import Path
import os,secrets,subprocess,sys
root=Path(__file__).resolve().parent
python=root/'.venv/bin/python'
if not python.exists():
    raise SystemExit('Crea .venv e instala requirements.lock.txt antes de iniciar. Ver README.md.')
folder=root/'data';folder.mkdir(exist_ok=True)
token=folder/'gateway.token'
if not token.exists():
    token.write_text(secrets.token_urlsafe(32));token.chmod(0o600)
env={**os.environ,'COBRANZA_TOKEN':token.read_text().strip()}
subprocess.run([str(python),str(root/'src/gateway.py')],env=env,check=True)
