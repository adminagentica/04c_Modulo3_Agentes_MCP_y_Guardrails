# Instalación local

Requisitos: Git, Python 3.11 o superior, Node 22.13 o superior con `node:sqlite`, pnpm 9, n8n local y Ollama. La configuración original se probó con Python 3.14, Node 22.22 y n8n 2.6.4. Usar un entorno aislado y puertos libres. No iniciar una segunda instancia sobre la demo que ya está funcionando.

## 1. Obtener y preparar

```sh
git clone https://github.com/adminagentica/04c_Modulo3_Agentes_MCP_y_Guardrails.git
cd 04c_Modulo3_Agentes_MCP_y_Guardrails
python3 -m venv demo/.venv
demo/.venv/bin/python -m pip install -r demo/requirements.lock.txt
python3 scripts/preparar.py
cd rag/03_Demo_Cobranza
pnpm install --frozen-lockfile
cd ../..
```

`preparar.py` crea un token local con permisos restringidos, inicializa solamente datos sintéticos e informa las rutas. No lee credenciales del docente, no instala cuentas y no llama modelos. El `.env.example` es una referencia: los scripts no cargan automáticamente archivos .env.

## 2. Modelos locales y RAG

```sh
ollama pull embeddinggemma:latest
ollama pull qwen3:4b
```

Ollama debe estar iniciado. En una terminal separada, desde la raíz:

```sh
cd rag/03_Demo_Cobranza
node server.js
```

La ingesta se inicia al arrancar el servicio. Comprueba `http://127.0.0.1:4173/api/rag/status`: debe quedar `ready`. La primera ingesta descarga/usa recursos locales y tarda según el equipo. No consume OpenAI. Los documentos y los modelos no deben cambiar durante una consulta.

## 3. Gateway y app

En otra terminal desde la raíz:

```sh
python3 demo/run_local.py
```

App: http://127.0.0.1:8790. Clave de demostración predeterminada: `DemoAgentica!2026`. Puede cambiarse exportando EXECUTIVE_DEMO_PASSWORD antes de iniciar. El token interno se lee desde demo/data/gateway.token y no se imprime.

## 4. n8n y credenciales

Abrir el n8n local en http://localhost:5678. Seguir docs/04_N8N.md. Los JSON no incluyen credenciales: hasta asignarlas y publicar el workflow, las consultas de la app no funcionarán. No se realiza importación automática sobre una instancia existente.

## 5. Clientes y comprobaciones gratuitas

```sh
python3 scripts/configurar_mcp.py --claude
python3 scripts/configurar_mcp.py --codex
python3 scripts/verificar.py
```

Instalar previamente los clientes que se quieran registrar. La configuración Claude se guarda en .mcp.json local; para Codex se registra una conexión con rutas absolutas. Reabrir el cliente para cargarla. Las verificaciones usan modelos simulados y no necesitan Gmail ni OpenAI.

Para apagar, detener cada terminal del servicio con Ctrl+C. No detener procesos de otras demos ni borrar las bases existentes. El repositorio se entrega sin bases; los saldos sintéticos se inicializan en cada instalación. El vencimiento se establece al crear el caso, cinco días antes, y luego se conserva.
