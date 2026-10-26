# Subagente RAG y corpus

Se incluye el RAG de Clase_Agentica: fuentes DOCX → extracción por secciones → embeddings locales → SQLite con vectores y FTS5 → búsqueda híbrida por coseno y BM25 → fusión RRF → evidencias.

| Fuente vigente | Versión |
|---|---|
| POL-COB-04 | v4 |
| POL-PAG-02 | v5 |
| POL-PRO-03 | v4 |
| MAN-ATN-02 | v3 |

El corpus contiene históricos para explicar trazabilidad. La ingesta usa el manifiesto y el filtro de vigencia, rol y estado; no debe aceptar un documento histórico solo por su parecido semántico. La ingesta original genera 26 fragmentos. El índice se construye localmente y no se publica su base SQLite.

## Configuración

Node resuelve `../05_Corpus_Documental` desde rag/03_Demo_Cobranza. Python resuelve `../rag/05_Corpus_Documental` desde demo. No depende del directorio en que se inicia el comando. Una ruta absoluta en COBRANZA_RAG_CORPUS permite elegir otro corpus autorizado; el RAG Node debe usar el mismo mediante CORPUS_DIR. Las huellas de los archivos tienen que coincidir.

Ollama usa embeddinggemma:latest y qwen3:4b. La ruta de la app recupera con embeddings y genera en OpenAI/n8n; la interfaz histórica del RAG también puede generar y reordenar con Qwen local. Cambiar el modelo de embeddings requiere reconstruir el índice.

## Contrato documental

Cada evidencia conserva ID de fragmento, código, versión, sección, contenido y hash. El backend compara estos valores con el índice y con las fuentes físicas antes de aceptar la respuesta. Un pasaje se trata como datos y no puede dar órdenes al orquestador. La validación de IDs y citas no garantiza por sí sola que una interpretación sea correcta: las Evals y la revisión humana comprueban apoyo semántico y pertinencia.

Si falta el servicio o evidencia en una consulta de saldo + recordatorio, se conserva el saldo verificado y se informa que la política necesita revisión. No se inventa una aprobación.

## Reconstrucción local

Con Ollama iniciado y modelos instalados:

```sh
cd rag/03_Demo_Cobranza
node local-rag-cli.mjs ingest
```

No ejecutarlo al mismo tiempo que otra ingesta sobre la misma base. Los modelos Ollama y el índice generado no forman parte de Git. Los manifiestos de fuentes sí se conservan para verificar procedencia.
