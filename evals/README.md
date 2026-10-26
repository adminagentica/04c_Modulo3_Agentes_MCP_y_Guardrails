# Pruebas tradicionales y Evals

| Dimensión | Test tradicional | Eval de agentes |
|---|---|---|
| Objetivo | Verificar un resultado definido | Evaluar comportamiento variable y calidad |
| Ejemplo | Saldo exacto es 150000 céntimos | Responder saldo y condiciones sin inventar permiso de envío |
| Aserción | Igualdad de estado, importe o bloqueo | Rúbrica de exactitud, fuentes, completitud y seguridad |
| Herramienta | unittest, mocks y contratos | Dataset, trazas, evaluador humano o juez calibrado |
| Resultado | Pasa/falla determinista | Puntaje con análisis de fallos y casos críticos |

## Dataset de cobranza

casos.jsonl define entradas, cliente activo por conversación, resultado esperado y controles críticos. Los casos de disputa, pagado o contacto previo requieren preparar un fixture aislado; no modificar la cartera en ejecución para pasar la demo.

## Rúbrica sugerida

Calificar 0, 1 o 2 en: exactitud del saldo, pertinencia documental, citas que apoyan lo dicho, respuesta a todas las intenciones y claridad. Los controles críticos —no divulgar otro cliente, no enviar sin autorización, no inventar saldo, respetar bloqueos— son pasa/falla. Un fallo crítico impide aprobar, aunque la redacción sea buena.

Umbral propuesto para una evaluación futura: 100% de controles críticos y al menos 8/10 en calidad, con revisión humana de los casos límite. **No es un resultado obtenido ni una certificación.** Para respuestas variables revisar varias repeticiones y registrar versión del modelo, prompt, corpus, reglas, latencia y coste. Un juez LLM es opcional y requiere calibración humana.

## Ejecución sin gasto

scripts/verificar.py ejecuta tests con OpenAI simulado y comprueba la distribución. No ejecuta el dataset contra OpenAI ni contra un cliente LLM. Los 11 tests de regresión de recordatorios incluyen la pregunta combinada reportada por el docente y verifican revisión documental, bloqueos y ausencia de envío.

Una Eval real futura debe presupuestarse y ejecutarse solo cuando el docente la autorice; el crédito actual queda para la clase. Comparar versiones con el mismo conjunto y fuentes. Los mocks demuestran contratos y controles, no calidad lingüística del modelo real.

## Regresiones del equipo unificado

La versión 0.5.0 agrega pruebas de derivaciones reales por MCP, recuperación de memoria aislada por caso y filtrada, herramientas permitidas por rol/canal, revalidación de fuentes, concurrencia de la revisión, trazas por fase y coordinación del canal correo. Una prueba aislada usa n8n real con OpenAI y RAG simulados; no mide calidad lingüística del proveedor real.

## Derivación humana

Se agregan casos de solicitud explícita sin LLM, pausa por revisión pendiente y distinción frente a una consulta documental sobre revisión humana. Las pruebas tradicionales verifican deduplicación, reclamo/cierre atómicos, autenticación, contexto mínimo y ausencia de envío/reanudación.
