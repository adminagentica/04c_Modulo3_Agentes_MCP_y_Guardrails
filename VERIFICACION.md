# Verificación de la entrega 0.4.1

- **79 pruebas Python aprobadas**, incluyendo la consulta combinada de saldo/recordatorio y la resolución portable del corpus. Las conexiones TCP del proceso de tests estuvieron bloqueadas.
- **30 pruebas del RAG aprobadas**, con modelos simulados y servidores de prueba locales.
- Workflows revisados: sin referencias a credenciales, sin pinData y desactivados en la distribución.
- Corpus incluido: cuatro DOCX vigentes, históricos y manifiestos de fuentes. La huella no depende del directorio de trabajo.
- No se llamó OpenAI ni se inició una ejecución de modelo Codex/Claude. No se enviaron correos.

Las pruebas comprueban implementación y contratos con respuestas simuladas. No certifican la calidad del modelo real ni sustituyen una evaluación humana de la política. Las Evals de evals/casos.jsonl son casos planificados, no resultados de un benchmark ejecutado con crédito real.

Los servicios y credenciales existentes del docente no se migraron ni se reemplazaron. Para una instalación nueva faltan dependencias locales, modelos Ollama, token propio y credenciales asignadas en n8n. La app consulta y evalúa elegibilidad; no envía recordatorios desde el chat.
