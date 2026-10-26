"""Inicializa datos y token nuevos; no conecta n8n ni proveedores externos."""
from pathlib import Path
import secrets,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'demo/src'))
from customer_service import CustomerService
folder=ROOT/'demo/data';folder.mkdir(exist_ok=True)
file=folder/'gateway.token'
if not file.exists():
    with file.open('x') as handle:handle.write(secrets.token_urlsafe(32))
    file.chmod(0o600)
service=CustomerService();service.store.seed();service.seed()
print('Datos sintéticos inicializados. Token local: demo/data/gateway.token (valor oculto).')
print('Configura las credenciales en n8n según docs/04_N8N.md; no se ha realizado ninguna llamada a modelos.')
