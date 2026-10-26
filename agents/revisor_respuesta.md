---
id: revisor_respuesta
version: 1.0.0
team_version: 1.3.0
---
# Revisor respuesta

**Descripción:** Revalida el contrato, las fuentes y el estado actual del caso antes de entregar la respuesta.

**Ejecución y LLM:** Especialista determinista; no requiere LLM.

**Invocado por:** orquestador. No delega a otros especialistas.

**Herramientas:** saldo_cliente y verificar_contexto

**Entrada:** Salida del redactor, contexto conservado, huella del caso, RAG y necesidad de revisar contacto.

**Salida:** Contrato validado, verified y reminder_check actualizado; revisión explícita ante respaldo insuficiente.

**Reglas internas:** Rechazar citas inventadas y cambios de caso. Los IDs válidos no garantizan por sí solos apoyo semántico; las Evals revisan esa calidad.

**Memoria:** no lee ni escribe memoria libre. El supervisor realiza recuperación filtrada y registro de eventos validados del mismo caso.

**Parada:** error de contrato, permisos, ámbito, evidencia o herramienta. Registrar el fallo y devolver el control al supervisor; no ampliar herramientas ni reintentar automáticamente.
