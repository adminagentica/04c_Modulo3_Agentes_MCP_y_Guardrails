# Contrato de derivación humana

**Versión:** 1.0.0. **Invoca:** orquestador mediante MCP derivar_a_humano. **Responsable de la decisión:** ejecutivo autenticado, no otro LLM.

**Entrada:** request_id y caso validados capturados por el supervisor; motivo tipado. No se envía la pregunta completa, DNI o correo.

**Salida:** ticket con ID, motivo, estado, contexto mínimo y automation_paused. El ticket no implica que se haya enviado una notificación ni atendido al cliente.

**Flujo:** pendiente → tomar caso → en revisión → registrar decisión → resuelta. Reclamo y cierre atómicos. Sin reanudación o correo automático.

**Herramientas del modelo:** solo creación. Tomar y resolver se realiza en la bandeja por el operador autorizado. No conceder al modelo herramientas de aprobación o cierre.

Ver [guía operativa](../docs/10_DERIVACION_HUMANA.md).
