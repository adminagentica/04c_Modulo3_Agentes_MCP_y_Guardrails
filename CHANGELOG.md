# 0.8.1

- Agente revisor guardrails para Codex/Claude, catálogo de 67 controles y guion de clase; sin nuevas llamadas en n8n.

- Dos clientes aptos y dos con bloqueo/derivación humana adicionales, con facturas independientes y accesos en la app.

- Cliente activo obtenido del DNI escrito, sin selector obligatorio; seguimiento y restauración por conversación.
- Cambio de cliente invalida borradores pendientes y evita completar una respuesta del contexto anterior.
- Gmail mantiene la validación correo + DNI. Pruebas sin consumo de modelos ni envío real.

# 0.8.0

- Borrador local completo al consultar saldo y recordatorio, con confirmación en el siguiente turno.
- Memoria conversacional persistente, restauración del chat y confirmación del borrador exacto mostrado.
- Envío Gmail por n8n con revalidación, reserva única, deduplicación y derivación ante resultado incierto.
- Mismo contrato para app y clientes MCP Codex/Claude; pruebas aisladas sin consumo ni correo real.

# Cambios

## 0.7.0 · OpenAI en el RAG, casos y citas
- Generación documental independiente mediante OpenAI/n8n con clave cifrada existente; embeddings locales.
- Sin reintentos ni fallback; RRF evita otra llamada de reordenamiento.
- Clientes apto y bloqueado con controles operativos explícitos; bloqueo antes del LLM.
- Máximo tres secciones pertinentes para contacto y enlaces solo de citas usadas.
- Registro separado de la prueba real del usuario (ejecución 25).

## 0.6.0 · Derivación humana
- Ticket local mediante MCP con motivos y contexto mínimo; solicitud explícita sin LLM.
- Bandeja autenticada: pendiente, en revisión y resuelta; reclamo/cierre atómicos.
- Bloqueo de contacto y de reservas Gmail durante la revisión; sin reanudación automática.
- Registro en memoria y auditoría; el modelo no dispone de herramientas para resolver.

## 0.5.0 · Equipo unificado
- Supervisor ejecutable común para consultas y coordinación del canal Gmail.
- Derivación real a especialistas mediante cliente/servidor MCP del SDK Python con transporte en memoria.
- Lectura de memoria filtrada por caso y escritura de eventos validados; traza de roles, versiones y herramientas.
- Revisor con revalidación de fuentes, huella e historial; control de concurrencia y permisos por canal.
- Recorrido visible en la app; máximo una llamada OpenAI por consulta.
- El motor anterior de cuatro roles se conserva como ejercicio histórico.

## 0.4.1 · Entrega de clase
- Incluye RAG, corpus documental y demo de cobranza en un repositorio portable.
- Agrega instrucciones para Codex y Claude Code, contratos de agentes, guion y Evals.
- Corrige la consulta combinada de saldo y recordatorio: evalúa reglas, recupera políticas y devuelve ambas partes; no envía mensajes.
- Revalida los controles de contacto al completar la respuesta. Si no hay evidencia, preserva el saldo y señala la revisión pendiente.
- Elimina credenciales de los workflows de distribución y no incluye memoria ni ejecuciones del equipo original.
- La configuración del corpus resuelve rutas desde el componente, sin depender del nombre de usuario del docente.

## Límites actuales
La app permite consultar y evaluar; no tiene un botón de envío de recordatorios. El recorrido Gmail responde consultas de prueba y no es un recordatorio saliente programado. La coincidencia correo/DNI no es una verificación de identidad fuerte. La autenticación del ejecutivo es de demostración. El índice usa búsqueda exacta por coseno y FTS5; no es una base vectorial distribuida. Los roles Markdown describen la delegación y no se convierten solos en procesos autónomos.
