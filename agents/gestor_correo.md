---
id: gestor_correo
version: 1.0.0
team_version: 1.2.0
---
# Gestor correo

**Descripción:** Coordina consultas entrantes de prueba en las fases de preparación, reserva y confirmación.

**Ejecución y LLM:** Especialista determinista; no requiere LLM.

**Invocado por:** orquestador. No delega a otros especialistas.

**Herramientas:** preparar_consulta_correo, reservar_respuesta_correo y confirmar_envio_correo; solo en el canal correo.

**Entrada:** Mensaje Gmail o reserva, según la fase autorizada del workflow.

**Salida:** Identidad/should_send, estado de reserva o gmail_accepted con ID confirmado por n8n.

**Reglas internas:** El envío físico pertenece al nodo Gmail Send. No cambiar destinatario desde el cuerpo, repetir reservas o reintentar un envío incierto.

**Memoria:** no lee ni escribe memoria libre. El supervisor realiza recuperación filtrada y registro de eventos validados del mismo caso.

**Parada:** error de contrato, permisos, ámbito, evidencia o herramienta. Registrar el fallo y devolver el control al supervisor; no ampliar herramientas ni reintentar automáticamente.
