# Verificación 0.6.0 · Derivación humana

- **117 tests Python aprobados**, con conexiones TCP bloqueadas; **30 tests del RAG aprobados**, con modelos simulados.
- Flujo positivo en n8n aislado aprobado con RAG y OpenAI simulados.
- Flujo de derivación humana en n8n aislado aprobado: el nodo que reemplaza al modelo lanza un error si se ejecuta; la solicitud terminó por la rama sin LLM y creó un ticket pendiente mediante MCP.
- Bandeja probada en Chrome con base temporal: pendiente → tomar caso → en revisión → seleccionar decisión explícita → registrar resolución. El botón de cierre permanece deshabilitado hasta seleccionar una decisión.
- Comprobados contexto mínimo, memoria/auditoría, deduplicación, concurrencia, autenticación, bloqueo de contacto y bloqueo de reserva Gmail.
- **Cero llamadas OpenAI y cero correos enviados durante las pruebas.** No se atendieron ni cerraron solicitudes reales; todos los tickets de prueba fueron temporales.

La captura en docs/images corresponde al entorno temporal de prueba. No se incluyen bases, sesiones o credenciales. La bandeja no notifica a un humano externo; requiere que el ejecutivo ingrese. El rol fijo ejecutivo-demo no es autenticación empresarial. Resolver no autoriza envíos ni reanuda procesos.

Conexión local publicada comprobada: versión 0.6.0, equipo 1.1.0 y RAG ready. La ejecución n8n 24 rechazó un DNI discordante antes del modelo; se inspeccionaron sus nodos y se confirmó que OpenAI no se ejecutó. No se crearon tickets de prueba en la instancia de clase.
