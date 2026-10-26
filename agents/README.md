# Equipo principal de agentes

La versión 0.5.0 conecta un supervisor y especialistas reales de software. El registro ejecutado es demo/config/team.json y la coordinación está en demo/src/agent_team.py. App y Codex/Claude llegan al mismo workflow; Gmail usa el mismo supervisor con capacidades separadas.

| Rol | Ejecución | Contrato |
|---|---|---|
| orquestador | Supervisor determinista | [Derivación y memoria](orquestador.md) |
| analista_saldo | Especialista SQL mediante MCP | [Saldo](analista_saldo.md) |
| analista_elegibilidad | Especialista de reglas mediante MCP | [Contacto](analista_elegibilidad.md) |
| rag_politicas | Recuperador documental mediante MCP | [RAG](rag_politicas.md) |
| redactor_respuesta | LLM en n8n | [Respuesta estructurada](redactor_respuesta.md) |
| revisor_respuesta | Especialista de validación mediante MCP | [Revisión](revisor_respuesta.md) |
| gestor_correo | Especialista del canal Gmail mediante MCP | [Correo](gestor_correo.md) |

Solo el redactor de la ruta principal invoca OpenAI: máximo una llamada por consulta. Los demás módulos aplican procedimientos acotados y verificables; no son LLM independientes. El supervisor registra cada derivación y limita herramientas por rol/canal.

Los archivos analista.md, redactor.md y revisor.md describen el ejercicio histórico de cuatro roles LLM de cobranza.py/config/agents.json. Se conservan para comparar enfoques, pero no sustituyen el equipo principal ni se ejecutan adicionalmente por cada pregunta. Las definiciones nativas Codex/Claude son clientes de consulta; no crean automáticamente procesos para estos módulos.
