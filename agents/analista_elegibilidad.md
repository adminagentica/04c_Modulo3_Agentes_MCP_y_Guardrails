---
id: analista_elegibilidad
version: 1.1.0
team_version: 1.2.0
---
# Analista elegibilidad

**Descripción:** Evalúa si los controles operativos permiten preparar un borrador de prueba.

**Ejecución y LLM:** Especialista determinista; no requiere LLM.

**Invocado por:** orquestador. No delega a otros especialistas.

**Herramientas:** evaluar_contacto

**Entrada:** Cliente previamente validado en la misma sesión MCP.

**Salida:** can_prepare, blocking_reasons, recipient del registro, scope de prueba, requires_explicit_confirmation y sent=false.

**Reglas internas:** Nunca enviar ni reservar correos desde esta consulta. Preservar bloqueos por disputa, saldo cero, consentimiento, contacto previo o destinatario.

**Memoria:** no lee ni escribe memoria libre. El supervisor realiza recuperación filtrada y registro de eventos validados del mismo caso.

**Parada:** error de contrato, permisos, ámbito, evidencia o herramienta. Registrar el fallo y devolver el control al supervisor; no ampliar herramientas ni reintentar automáticamente.

Comprobar inquiry_contact_controls y días de atraso: no inferir ausencia de excepciones por falta de registros. Un pago pendiente remite a POL-PAG-02 §4 y detiene el flujo antes del LLM.
