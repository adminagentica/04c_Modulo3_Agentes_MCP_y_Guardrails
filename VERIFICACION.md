# Verificación 0.8.1

- 157 pruebas Python aprobadas, con conexiones TCP bloqueadas.
- 40 pruebas RAG aprobadas, con modelos simulados.
- Nuevos casos: DNI explícito sin selector, prioridad sobre contexto antiguo, seguimiento sin DNI, dos DNI ambiguos, cambio de cliente e invalidación del borrador, cambio después de aprobar antes de reservar, aislamiento por conversación, respuesta tardía y migración de memoria.
- App aislada: consulta sin selector → seguimiento sin DNI → cambio de cliente → borrador anterior bloqueado → historial y cliente restaurados al recargar, aprobado.
- n8n aislado: preparación → confirmación → Gmail simulado → repetición sin duplicado, aprobado.
- Runtime local: 0.8.1, RAG ready; ejecución 39 rechaza dos DNI sin invocar modelo.
- Cero llamadas pagadas y cero correos reales durante estas verificaciones.

La validación correo registrado + DNI del canal Gmail permanece igual. Los envíos reales se ejecutan solo ante la confirmación expresa del operador de un borrador válido; no se probaron con Gmail real durante esta preparación.

## Casos adicionales

Se agregaron 73148265 y 74259316 (aptos), y 75361428 y 76482539 (pago pendiente de conciliación). Verificación focalizada: reglas y saldos de los cuatro; derivaciones humanas de ambos bloqueos en base temporal; carga idempotente. En la base local se verificó que los casos anteriores y los conteos de envíos/tickets permanecen iguales. No se crearon tickets reales ni se enviaron correos al cargar los datos.
