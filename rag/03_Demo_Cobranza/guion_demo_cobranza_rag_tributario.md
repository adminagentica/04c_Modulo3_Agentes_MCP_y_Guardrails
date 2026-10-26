# Guion de demo: Agente de Cobranza y RAG Tributario

## Recorrido actual: RAG real y Ground Truth

Iniciar con `npm run demo:local` y abrir http://localhost:4173/. Esperar el estado de índice listo: cuatro Word reales, 26 fragmentos, 768 dimensiones.

1. Abrir una fuente del panel y descargar su Word. Comparar sección, versión y huella del archivo.
2. Preguntar «¿Qué información debe contener una promesa de pago?». Mostrar respuesta, cita y contexto realmente enviado a Qwen.
3. Abrir Ground Truth: revisar pregunta, respuesta esperada y cita textual. Los cuatro ejemplos tienen aprobación experta simulada, con revisor ficticio y fecha; están listos para el recorrido docente.
4. Distinguir la aprobación de la referencia de la revisión de cada respuesta del modelo. Los casos nuevos se crean como borradores y deben revisarse antes de validarse.
5. Seleccionar casos y ejecutar. Comparar esperado y obtenido, recuperación, cita y abstención.
6. Revisar fidelidad y completitud, y registrar acierto o fallo. Una respuesta que solo dice «No» puede citar la sección correcta y seguir siendo incompleta.
7. Ejecutar el caso de pago pendiente. Mostrar cómo los datos operativos activan la pausa y la política documental explica su fundamento. El envío permanece en vista previa.

En este modo, los embeddings, el re-ranking y la generación usan Ollama. La base local es SQLite con similitud coseno exacta y BM25. Las funciones del orquestador coordinan el flujo. Las consultas pueden tardar varias decenas de segundos.

Los recorridos siguientes corresponden a las simulaciones anteriores (`npm run demo:clase`), no al modo real predeterminado.

## Recorrido 1: explicar la diapositiva 33

Abrir la página principal en `http://localhost:4173`. Para una clase sin PostgreSQL, iniciar con `npm run demo:clase`. La cabecera identifica el modo de datos y la simulación del envío.

1. Ejecutar **Deuda: propuesta para revisión**. Mostrar DNI, pregunta y orquestador.
2. Abrir **Datos operativos**. Distinguir saldo e historial de las políticas documentales. Los importes provienen de SQL/API o de los casos incorporados, según el modo.
3. Abrir **Embedding de consulta**. Mostrar cómo la consulta de recuperación incorpora señales del caso y produce cuatro valores didácticos.
4. Abrir **Búsqueda híbrida y fusión**. Comparar las posiciones vectoriales y léxicas con el ranking RRF.
5. Abrir **Re-ranking y contexto**. Comparar el orden antes y después, y desplegar los pasajes con documento, versión y sección.
6. Abrir **¿Se puede actuar?**. La propuesta permanece pendiente de revisión humana.
7. Revisar la **Respuesta fundamentada** y su cita. Aclarar que el demo usa una plantilla reproducible, no un LLM real.
8. Revisar el mensaje y el contacto, marcar la revisión y aprobar. Procesar WhatsApp en modo simulado. Mostrar que editar el texto invalida la aprobación.
9. Ejecutar **Pago pendiente: pausar y conciliar**. El pago pendiente prevalece sobre la deuda y la promesa incumplida. La acción de contacto queda bloqueada.
10. Comparar **Atención especial**, **Promesa incumplida** y **Política inexistente**. Observar las distintas razones para detener o escalar.
11. Si se quiere mostrar correo, seleccionar el caso de canal autorizado por correo y abrir solo el borrador aprobado. No se envía automáticamente.

Los especialistas de esta implementación son funciones del programa. La representación vectorial de cuatro dimensiones y el re-ranking por reglas son recursos docentes. PostgreSQL utiliza full-text, no BM25. El perfil de asesor o supervisor simula permisos y no constituye autenticación real.

## Recorrido 2: RAG tributario

Este recorrido corresponde al archivo independiente `demo_agente_cobranza_rag_tributario.html`, no a la página principal ajustada a la diapositiva 33.

1. Seleccionar **RAG Tributario**.
2. Ejecutar la consulta sobre recibo por honorarios.
3. Comparar recuperación léxica e híbrida.
4. Revisar identificador, versión, sección y texto recuperado.
5. Ejecutar **Caso sin fuente aprobada**. La salida correcta debe abstenerse y derivar.

## Ground truth mínimo

| Ruta | Caso | Tool o fuente esperada | Salida esperada |
|---|---|---|---|
| Cobranza | Deuda dentro de política | obligations + POL-COB-04 | Propuesta para revisión |
| Cobranza | Pago pendiente de aplicación | payment_history + POL-PAG-02 |  Pausar contacto y conciliar |
| Cobranza | Atención especial | customers.special_attention + MAN-ATN-02 |  Derivación humana |
| Cobranza | Promesa incumplida | payment_history + POL-PRO-03 |  Revisión humana |
| Tributario | Fuente vigente | Documento y sección esperados | Respuesta con cita y revisión |
| Tributario | Sin evidencia suficiente | Ninguna fuente válida | Abstenerse y derivar |

Todos los datos, políticas y documentos de la demostración son ficticios.
