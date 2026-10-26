# Instrucciones para Claude Code

Lee y aplica AGENTS.md, README.md y docs/06_CODEX_CLAUDE.md. El objetivo es la misma demo y las mismas restricciones de presupuesto y correo.

Para consultas funcionales usa exclusivamente la herramienta `consultar_orquestador` del servidor MCP `cobranza_local`, con la pregunta y el conversation_id conservado; el DNI explícito de la pregunta establece el contexto. El modelo de Claude Code es el configurado por el usuario; el LLM del workflow n8n es gpt-5.4-mini. Son configuraciones independientes.

No invoques consultas positivas durante pruebas: consumen el saldo reservado para clase. El envío ocurre únicamente en n8n tras mostrar el borrador y recibir «Envíalo» del operador. Conserva conversation_id y draft.id entre consultas; pasa draft_id en la confirmación. Nunca inventes esa aprobación. El rol nativo de consulta está en .claude/agents/consultas-cobranza.md; los contratos restantes están en agents/. La delegación de estos roles es explícita, no automática por existir archivos Markdown.

La revisión humana se gestiona en la bandeja autenticada. No tomar ni resolver tickets reales o representar una aprobación humana por iniciativa del modelo. Conservar human_handoff y automation_paused al devolver la respuesta del workflow.

El cliente activo del chat se establece por el DNI de la pregunta, sin selector obligatorio. Cambiarlo invalida borradores pendientes; nunca reutilizar un borrador de otro cliente.

El subagente guardrails está en .claude/agents/guardrails.md; su contrato completo, en agents/guardrails.md. Usarlo solo cuando el docente solicite esa revisión. No consulta el workflow ni envía correos.
