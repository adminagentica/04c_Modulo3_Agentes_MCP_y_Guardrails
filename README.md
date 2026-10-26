# Módulo 3 · Agentes, MCP y Guardrails

Demo de cobranza de Agentica · versión **0.4.1** · datos completamente sintéticos.

Construimos un asistente para el ejecutivo, un orquestador con memoria, un subagente RAG documental, reglas de negocio y un MCP en Python. La app y el cliente Codex/Claude consultan **el mismo workflow n8n local**. Un workflow separado responde consultas de deuda recibidas por Gmail.

**Empieza aquí:** [instalación](docs/02_INSTALACION.md), [guion de clase](docs/03_GUION_CLASE.md) y [arquitectura](docs/01_ARQUITECTURA.md).

| Carpeta | Contenido |
|---|---|
| `demo/` | App del ejecutivo, gateway y MCP Python, memoria, reglas, pruebas y workflows n8n |
| `rag/03_Demo_Cobranza/` | Implementación RAG original incluida y sus pruebas |
| `rag/05_Corpus_Documental/` | Cuatro políticas/manuales vigentes, históricos y manifiestos |
| `agents/` | Contratos y prompts de los agentes en Markdown |
| `docs/` | Instalación, clase, n8n, RAG, correo, memoria y publicación |
| `evals/` | Casos y criterios de evaluación del sistema |
| `scripts/` | Preparación local, configuración MCP y verificación sin OpenAI |
| `AGENTS.md`, `CLAUDE.md` | Instrucciones de trabajo para Codex y Claude Code |

## Qué se ejecuta en cada recorrido

1. **App o cliente MCP → n8n:** valida el DNI seleccionado, consulta SQL y RAG si corresponde, hace como máximo una llamada a OpenAI y valida la respuesta. Saldo + recordatorio se resuelven como dos intenciones. Consultar elegibilidad no envía correo.
2. **Multiagente didáctico:** el motor incluido organiza orquestador → analista → redactor → revisor. Sus modos con modelos reales son opcionales y consumen recursos; no se ejecutan durante la preparación.
3. **Gmail:** recibe una consulta de prueba, compara correo y DNI, reserva una respuesta, envía por Gmail y registra el ID. El cliente autorizado es la misma cuenta de prueba. No utiliza OpenAI.

El RAG es documental: **SQL calcula el saldo; el RAG aporta políticas**. Las reglas, los permisos y las escrituras permanecen fuera del modelo. MCP es la interfaz de herramientas y no equivale a otro LLM.

## Documentación

- [Diseño y flujo manual](docs/00_PLANIFICACION.md)
- [Arquitectura y recorridos](docs/01_ARQUITECTURA.md)
- [Instalación reproducible](docs/02_INSTALACION.md)
- [Guion para el docente](docs/03_GUION_CLASE.md)
- [Configuración de n8n](docs/04_N8N.md)
- [RAG y corpus](docs/05_RAG.md)
- [Codex y Claude Code](docs/06_CODEX_CLAUDE.md)
- [Correo e identidad](docs/07_CORREO.md)
- [Memoria, guardrails y fallos](docs/08_MEMORIA_GUARDRAILS.md)
- [Pruebas tradicionales y Evals](evals/README.md)
- [Publicación y entrega](docs/09_REPOSITORIO.md)
- [Cambios y límites](CHANGELOG.md)

**Presupuesto:** las pruebas automáticas no llaman OpenAI. Una consulta válida enviada por una persona a la app o al MCP sí puede consumir crédito de la credencial de n8n. Los modelos de los clientes Codex/Claude tienen su propio consumo. El crédito de la clase queda reservado.

No se incluyen claves, tokens, sesiones, bases con memoria anterior ni credenciales de n8n. No se transfieren automáticamente las credenciales que ya existen en el equipo del docente. Los modelos Ollama se descargan por separado.
