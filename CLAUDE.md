# Instrucciones para Claude Code

Lee y aplica AGENTS.md, README.md y docs/06_CODEX_CLAUDE.md. El objetivo es la misma demo y las mismas restricciones de presupuesto y correo.

Para consultas funcionales usa exclusivamente la herramienta `consultar_orquestador` del servidor MCP `cobranza_local`, con la pregunta y el DNI seleccionado por el operador. El modelo de Claude Code es el configurado por el usuario; el LLM del workflow n8n es gpt-5.4-mini. Son configuraciones independientes.

No invoques consultas positivas durante pruebas: consumen el saldo reservado para clase. No envíes correo desde el cliente. El rol nativo de consulta está en .claude/agents/consultas-cobranza.md; los contratos restantes están en agents/. La delegación de estos roles es explícita, no automática por existir archivos Markdown.

La revisión humana se gestiona en la bandeja autenticada. No tomar ni resolver tickets reales o representar una aprobación humana por iniciativa del modelo. Conservar human_handoff y automation_paused al devolver la respuesta del workflow.
