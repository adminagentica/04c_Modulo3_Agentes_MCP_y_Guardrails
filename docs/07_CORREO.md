# Gmail, identidad y envío

## Alcance actual

El workflow consulta-gmail responde una **consulta entrante** de deuda a través de MailOrchestrator, el supervisor común y el gestor de correo con herramientas MCP acotadas. No utiliza LLM ni RAG para una consulta exclusivamente de saldo. La app prepara un borrador local y, tras una confirmación explícita posterior, n8n puede enviarlo al único destinatario demo autorizado. Ver [borrador y confirmación](13_BORRADOR_Y_CONFIRMACION.md). El motor didáctico captura archivos .eml para destinatarios example.test. No mezclar estos tres comportamientos al enseñar la demo.

Solo el docente puede activar el recorrido real de prueba y revisar el buzón destinatario. La cuenta de demostración configurada es contacto@agentica.com.pe; para otro buzón de prueba se deben adaptar el registro sintético y los controles, con autorización explícita.

## Configuración local

1. Habilitar Gmail API en el proyecto Google Cloud autorizado.
2. Crear/configurar Gmail OAuth2 en n8n con su URI de retorno y consentir los permisos necesarios de lectura/envío.
3. Asignar esa credencial al trigger y al nodo Gmail Send.
4. Configurar Header Auth hacia el backend y comprobar el filtro de asunto.
5. Publicar solo cuando se quiera recibir y responder consultas reales de prueba.

No compartir client_secret, refresh_token, contraseñas o API keys en Markdown ni Git. Cada alumno conecta su propia cuenta autorizada.

## Mensaje sintético de la clase

- Desde y hacia: contacto@agentica.com.pe.
- Asunto: `AGENTICA-PRUEBA Consulta deuda`.
- Cuerpo: `Hola, deseo consultar mi deuda. Mi DNI es 74851236.`

El proveedor debe entregar las etiquetas SENT e INBOX para este autoenvío. El backend exige un único remitente, un DNI de ocho dígitos identificado como DNI y coincidencia exacta con el registro. No utiliza destinatarios del cuerpo o Reply-To. Un DNI ausente o inválido produce respuesta genérica sin saldo; un remitente fuera de la prueba no recibe respuesta. La coincidencia no verifica RENIEC ni identidad fuerte para datos reales.

## Estados

Mensaje entrante → preparado → reserva/claim → sending → sent con ID Gmail. El ID de mensaje entrante evita responder dos veces. Una huella verifica que no cambió el caso antes de enviar. Si el resultado del envío es incierto, revisar el buzón y la ejecución; no reintentar automáticamente ni eliminar el registro para forzar otro correo.

La prueba previa del docente comprobó una respuesta real con datos sintéticos. Sus mensajes, IDs, memoria y credenciales no forman parte de esta distribución; cada instalación comienza sin ese historial.

## Actualizar una instalación existente

No migrar tokens, credenciales ni historial al repositorio. Evitar actualizar mientras un correo está entre preparación, reserva y confirmación. Las reservas anteriores sin traza de supervisor requieren revisión manual; no se recrean ni se reintentan para forzar un envío.
