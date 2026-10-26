# Verificación de la entrega 0.5.0

- **98 pruebas Python aprobadas**, con conexiones TCP bloqueadas: contratos, delegación, protocolo MCP real en memoria, permisos por rol/canal, memoria aislada/filtrada, revisión de fuentes/caso, concurrencia, gateway y coordinación de correo.
- **30 pruebas del RAG aprobadas**, con modelos simulados y servidores locales.
- **Recorrido completo con n8n real aislado aprobado**, reemplazando OpenAI por un nodo Code y el RAG por un fixture. Se comprobó participación de supervisor, saldo, contacto, RAG, redactor y revisor, además de persistencia de la traza y memoria.
- JavaScript de la app comprobado sintácticamente. La traza se ofrece en «Ver recorrido del agente».
- **Cero llamadas OpenAI, cero ejecuciones de modelo Codex/Claude y cero correos enviados durante las pruebas.**

La traza de examples/traza-orquestacion-simulada.json está marcada como simulada: no es una respuesta de OpenAI real ni un envío de correo. Las confirmaciones Gmail en tests usan identificadores sintéticos sobre bases temporales y no contactan al proveedor.

El supervisor y los especialistas de datos/reglas son deterministas; el redactor es el único rol LLM de la ruta principal. Esta entrega no certifica calidad semántica del modelo real, identidad fuerte de clientes ni preparación para producción. El motor histórico de cuatro roles se mantiene aparte como ejercicio.

La distribución no incluye credenciales, tokens, memoria del docente o modelos descargados. La actualización de código conserva los endpoints y el webhook existentes; una instalación nueva configura su propio entorno y credenciales.

La conexión local publicada se verificó con un DNI discordante: ejecución n8n 23, respuesta clarify, modelo no-invocado y solo nodos de entrada/contexto/condición/aclaración. La inspección de la ejecución confirmó que el nodo OpenAI no se ejecutó. La app informa versión 0.5.0 y el RAG está ready.
