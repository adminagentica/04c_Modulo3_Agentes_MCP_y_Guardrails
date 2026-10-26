# Módulo 3 · Agentes, MCP y Guardrails

Demo de cobranza de Agentica · versión **0.7.0** · datos completamente sintéticos.

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

## Un solo equipo orquestado

El supervisor deriva a **analista de saldo, analista de contacto, especialista RAG, redactor y revisor** según la intención. Recupera memoria del caso, llama capacidades mediante MCP Python real y guarda eventos validados. El canal Gmail usa el mismo supervisor con el gestor de correo. Cada respuesta incluye la traza de los pasos ejecutados, visible en la app.

El redactor usa gpt-5.4-mini en n8n; los otros especialistas son módulos deterministas acotados. Se mantiene un máximo de una llamada OpenAI por consulta. No es una cadena de siete LLM ni un planificador de delegación libre. Las reglas y escrituras críticas permanecen en el backend.

MCP público conecta Codex/Claude con el workflow. MCP interno conecta especialistas y herramientas mediante el SDK oficial y transporte en memoria, con capacidades separadas para consulta y correo. [Ver el diagrama y los límites](docs/01_ARQUITECTURA.md).

El RAG aporta documentación; SQL aporta los montos; la memoria aporta contexto previo del mismo caso. Consultar si procede un recordatorio no envía correo. El envío Gmail real sigue dentro de n8n, después de validar y reservar la respuesta.

El motor didáctico anterior de cuatro roles LLM se conserva como ejercicio histórico; el registro del equipo principal es demo/config/team.json.

## Derivación humana

El supervisor crea una derivación cuando se solicita un ejecutivo, falta evidencia, hay un bloqueo de contacto o falla la validación/proveedor. La app incluye **Atención humana**: pendiente → en revisión → resuelta. El ticket conserva contexto mínimo, memoria y auditoría. Tomar o resolver un caso no envía correo ni reanuda acciones. [Ver el flujo completo](docs/10_DERIVACION_HUMANA.md).

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

Ver [clientes y citas](docs/11_CASOS_Y_CITAS.md) y [RAG con OpenAI](docs/12_RAG_OPENAI.md).
