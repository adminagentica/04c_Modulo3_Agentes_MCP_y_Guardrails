# Memoria y guardrails

## Memoria del orquestador

SQLite guarda eventos tipados por tenant_id y case_id. Vigencia predeterminada: 30 días; recuperación máxima: 12 eventos. Ejemplos: reglas evaluadas, identidad validada, agente completado y aceptación por Gmail. Registrar versión del agente, ejecución y resultado validado; no razonamientos internos, secretos o instrucciones arbitrarias. Recordar que antes se pudo contactar no autoriza un nuevo contacto.

El índice documental y el historial de un caso son almacenes distintos. No enviar toda la memoria a un modelo sin filtrar. La distribución no copia las bases existentes del docente.

## Guardrails por capa

| Capa | Ejemplo | Resultado |
|---|---|---|
| Entrada | DNI escrito distinto al seleccionado | Aclaración sin OpenAI ni divulgación |
| Identidad por correo | Remitente no autorizado | Rechazo sin respuesta de deuda |
| Datos | Monto SQL difiere de lo propuesto | Mostrar solo importe del backend |
| Documentación | Cita inventada o índice modificado | Rechazo o revisión |
| Negocio | Caso pagado/disputado/sin consentimiento | Bloquear preparación de contacto |
| Contacto | Recordatorio reservado o contacto reciente | Evitar duplicidad y respetar intervalo |
| Acción | Consulta sobre envío | Evaluación; no ejecutar correo |
| Salida | JSON fuera del contrato | Detener y registrar |
| Entorno | API key o token en archivo público | Fallar la revisión de distribución |

Las reglas del motor original mantienen destinatarios example.test. Solo la evaluación de vista previa del caso sintético MAIL-DEMO permite valorar la cuenta de autoenvío autorizada; esto no cambia las reglas de envío del motor. El backend vuelve a comprobar historial al completar la consulta.

## Fallos previstos

RAG no disponible → saldo exacto y revisión documental pendiente en la pregunta combinada. Modelo sin citas → conservar controles y pedir revisión concreta. Cambio de saldo durante la consulta → detener y pedir nueva consulta. OpenAI sin crédito o credencial → mensaje explícito, sin reintento automático. Gmail incierto → revisión humana antes de reintentar.

Estos controles cubren escenarios concretos. No presentar un caso de DNI discordante como protección universal ante prompt injection.
