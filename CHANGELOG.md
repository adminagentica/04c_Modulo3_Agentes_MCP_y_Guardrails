# Cambios

## 0.4.1 · Entrega de clase
- Incluye RAG, corpus documental y demo de cobranza en un repositorio portable.
- Agrega instrucciones para Codex y Claude Code, contratos de agentes, guion y Evals.
- Corrige la consulta combinada de saldo y recordatorio: evalúa reglas, recupera políticas y devuelve ambas partes; no envía mensajes.
- Revalida los controles de contacto al completar la respuesta. Si no hay evidencia, preserva el saldo y señala la revisión pendiente.
- Elimina credenciales de los workflows de distribución y no incluye memoria ni ejecuciones del equipo original.
- La configuración del corpus resuelve rutas desde el componente, sin depender del nombre de usuario del docente.

## Límites actuales
La app permite consultar y evaluar; no tiene un botón de envío de recordatorios. El recorrido Gmail responde consultas de prueba y no es un recordatorio saliente programado. La coincidencia correo/DNI no es una verificación de identidad fuerte. La autenticación del ejecutivo es de demostración. El índice usa búsqueda exacta por coseno y FTS5; no es una base vectorial distribuida. Los roles Markdown describen la delegación y no se convierten solos en procesos autónomos.
