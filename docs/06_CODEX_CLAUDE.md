# Usar la demo desde Codex o Claude Code

Ambos clientes actúan como ejecutivos de consulta. Se conectan al MCP Python con perfil `codex`, que expone únicamente `consultar_orquestador`. El nombre del perfil se conserva por compatibilidad; también sirve para Claude Code. La herramienta deriva al mismo workflow n8n de la app.

## Instrucciones y roles

- Codex lee AGENTS.md. Claude Code lee CLAUDE.md, que remite a las reglas comunes.
- agents/*.md contiene los contratos, límites y formatos de cada rol.
- .claude/agents/consultas-cobranza.md es una definición de subagente nativo de consulta, cuyo uso es explícito.
- .codex/agents/cobranza_consultas.toml conserva una definición de rol Codex como ejemplo; registrar MCP no inicia automáticamente ese agente ni una cuadrilla.

El modelo de ejecución de Codex/Claude es el elegido en el cliente. El LLM de negocio del workflow es gpt-5.4-mini y sus credenciales viven en n8n. Definir un archivo Markdown no crea otro proceso, no le concede herramientas y no concede permiso para enviar correos.

## Registrar MCP

Después de instalar demo/.venv y ejecutar scripts/preparar.py:

```sh
python3 scripts/configurar_mcp.py --claude
python3 scripts/configurar_mcp.py --codex
```

Para Claude se crea `.mcp.json` local con las rutas del equipo; si ya existe, el script se detiene para evitar sobrescribirla. Para Codex se usa `codex mcp add cobranza_clase` para no reemplazar una conexión `cobranza_local` del docente. El nombre de servidor en ese cliente será cobranza_clase; conserva la misma herramienta. Reiniciar o actualizar el cliente para cargar la conexión.

## Solicitud funcional

```text
Usa consultar_orquestador con dni_seleccionado="" y
pregunta="¿Cuál es el saldo y puedo preparar un recordatorio de deuda?".
Devuelve los controles, las fuentes y la referencia n8n. No envíes correos.
```

Esta consulta positiva puede consumir OpenAI y el modelo del cliente. Para demostrar un rechazo sin OpenAI, escribir dos DNI en la misma pregunta. El host sigue teniendo otros permisos y herramientas; el perfil MCP de consulta no aísla globalmente todo el cliente. AGENTS.md/CLAUDE.md limitan el comportamiento solicitado; los controles críticos se aplican en el backend.

## Mismo equipo que la app

consultar_orquestador deriva al mismo webhook y al supervisor de demo/config/team.json. La respuesta conserva agent_trace, versión del equipo, estado, fuentes y ejecución. No lanzar otros modelos o saltar a herramientas directas para simular la participación de especialistas. Los módulos internos son coordinados por el backend y sus herramientas MCP.

El DNI explícito de la pregunta establece el cliente activo. Conserva conversation_id para preguntas siguientes sin DNI. No es obligatorio proporcionar dni_seleccionado; el panel del chat refleja el contexto confirmado por el backend.

## Revisión de guardrails

El agente guardrails del cliente y su catálogo se documentan en [esta guía](14_AGENTE_GUARDRAILS.md). No es el revisor_respuesta determinista del workflow. La invocación es explícita y puede consumir cuota del cliente. No se ejecuta durante verificaciones preparatorias.
