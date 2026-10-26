# Agente guardrails para la clase

Este agente revisor reúne **67 controles** de la demo y explica dónde se aplican. El contrato completo está en [agents/guardrails.md](../agents/guardrails.md); el inventario estructurado, en [guardrails-reglas.json](../demo/config/guardrails-reglas.json).

## Qué aporta y qué ejecuta

El agente del cliente revisa código y evidencia suministrada y devuelve un informe. Los controles efectivos siguen ejecutándose en Python, SQLite, MCP y n8n. No se agregó otra llamada OpenAI al flujo de negocio ni se modificó el registro del equipo ejecutable. El revisor_respuesta actual continúa siendo determinista.

Abrir los Markdown o JSON en GitHub no consume tokens. Invocar el agente en Codex/Claude sí puede consumir crédito o cuota del cliente. No se lo ejecutó para verificar esta entrega.

## Archivos para mostrar

| Archivo | Qué mostrar |
|---|---|
| [Contrato del agente](../agents/guardrails.md) | Objetivo, modelo heredado, reglas internas, derivación, formato de respuesta y catálogo completo |
| [Catálogo JSON](../demo/config/guardrails-reglas.json) | ID, condición, efecto, archivo/función, canal y mecanismo de cada control |
| [Agente de Codex](../.codex/agents/guardrails.toml) | Definición del rol del cliente |
| [Agente de Claude Code](../.claude/agents/guardrails.md) | Definición del subagente con herramientas de lectura y búsqueda |

Codex descubre archivos de agentes por proyecto en las versiones que soportan esa función. Los permisos y MCP de la sesión padre se heredan: una instrucción de «solo revisión» no es una barrera de seguridad adicional. Ejecutarlo en una sesión con permisos de lectura adecuados si se necesita esa restricción. Claude restringe este subagente a Read, Glob y Grep. La lectura de archivos del repositorio no autoriza abrir secretos o datos locales.

## Encargos para usar después, por decisión del docente

```text
Usa el agente guardrails para explicar todos los controles de esta demo.
Lee agents/guardrails.md y su catálogo. Agrupa por entrada, identidad,
contacto, RAG, herramientas, aprobación, envío, memoria y revisión humana.
Para cada control muestra ID y archivo/función. No ejecutes consultas,
modelos de negocio, correos ni cambios. Separa código leído y pruebas existentes.
```

```text
Usa el agente guardrails para revisar el escenario sintético:
cliente 75361428 con pago pendiente de conciliación solicita un recordatorio.
Explica qué controles deben bloquearlo y cómo se deriva a una persona.
Solo revisa el código; no consultes la base ni el webhook y no crees un ticket.
```

```text
Usa el agente guardrails para explicar por qué un borrador de 74259316
no puede enviarse después de cambiar al cliente 40112233.
Identifica invalidación, confirmación, revalidación y reserva única.
No envíes el correo ni representes una aprobación humana.
```

## Guion de cinco minutos

1. Abrir el contrato: el revisor identifica controles; no concede permisos.
2. Mostrar en el catálogo las reglas de saldo, conciliación y revisión humana.
3. Ir a CustomerService.reminder_eligibility y Store.rules: el backend decide.
4. Mostrar ReminderActions.approve/check/claim: borrador exacto, confirmación, 30 minutos y reserva única.
5. Mostrar las limitaciones: sin clasificador general de ataques, sin prueba semántica universal de citas y sin identidad empresarial multiusuario.

Para comparar con Evals: el catálogo describe qué debería comprobarse; las pruebas ejercitan escenarios y verifican efectos. Un informe del agente sobre código no sustituye la ejecución de esas pruebas.

## Fuentes para el formato de agentes

- [Codex: subagentes y archivos TOML](https://learn.chatgpt.com/docs/agent-configuration/subagents)
- [Claude Code: subagentes y restricciones de herramientas](https://code.claude.com/docs/en/sub-agents)
