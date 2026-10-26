---
id: analista_saldo
version: 1.0.0
team_version: 1.1.0
---
# Analista saldo

**Descripción:** Obtiene saldo, factura y vencimiento exactos del cliente seleccionado.

**Ejecución y LLM:** Especialista determinista; no requiere LLM.

**Invocado por:** orquestador. No delega a otros especialistas.

**Herramientas:** saldo_cliente

**Entrada:** DNI seleccionado del contexto del operador; la sesión MCP lo captura, no acepta reemplazarlo mediante argumentos.

**Salida:** matched, account y fingerprint. Si matched=false, detener con aclaración.

**Reglas internas:** SQL es la fuente de verdad. No calcular cifras con RAG o texto del usuario.

**Memoria:** no lee ni escribe memoria libre. El supervisor realiza recuperación filtrada y registro de eventos validados del mismo caso.

**Parada:** error de contrato, permisos, ámbito, evidencia o herramienta. Registrar el fallo y devolver el control al supervisor; no ampliar herramientas ni reintentar automáticamente.
