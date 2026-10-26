# Verificación 0.7.0

- **125 tests Python y 40 tests Node/RAG aprobados.** Python bloqueó conexiones TCP; los proveedores se simularon.
- Puente de generación RAG aprobado en n8n aislado, sustituyendo OpenAI por un nodo Code. Comprobados límites de entrada, esquema estricto, modelo fijo, ausencia de reintentos y selección RRF sin una segunda llamada.
- Cliente 71425836 comprobado localmente: PEN 850.00, historial/promesas verificados, cinco días de atraso y sin bloqueos; requiere aprobación antes de enviar un recordatorio.
- Cliente 72536914 probado en el workflow local: PEN 1200.00 y pago pendiente. Ejecución 26: needs_review, POL-PAG-02 §4, derivación humana y **nodo OpenAI no ejecutado**, comprobado al leer sus nodos.
- RAG local ready con generación OpenAI y embeddinggemma local. Workflow adicional publicado usando la misma referencia de credencial que la app; no se extrajo la API key.
- **Cero llamadas pagadas y cero correos enviados por las pruebas de preparación.** La ejecución real 25 fue realizada por el usuario y consumió 2091 tokens; está registrada por separado en evals/manual/ejecucion25.json.

No se ejecutó otra generación real para medir mejora semántica. Los IDs correctos no demuestran por sí solos que una frase esté sustentada. La selección de citas se acota a secciones pertinentes y el backend solo muestra enlaces realmente usados; se mantiene revisión humana.

El caso bloqueado deja una derivación pendiente en la bandeja local para que el docente muestre la atención humana. No se cerró ni se aprobó automáticamente. La app no envía recordatorios por una consulta; la respuesta Gmail de prueba mantiene su recorrido controlado y su cuenta autorizada.
