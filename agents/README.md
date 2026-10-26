# Contratos de agentes

Estos Markdown describen responsabilidad, entrada, salida y límites. La ejecución implementada está en demo/config/agents.json, demo/config/rag-agent.json y el backend. La rama de consulta usa un LLM y un recuperador documental; el multiagente didáctico ejecuta cuatro roles secuenciales. No afirmar que todos se ejecutan por cada pregunta.

Los modelos del workflow se configuran en Python/n8n; los del cliente dependen de Codex o Claude. Los roles de analista, redactor y revisor no se habilitan como agentes nativos con permisos nuevos por copiar estos archivos. Para invocarlos en otro host, conservar el contrato y validar sus salidas en el backend.

Orden: orquestador → RAG/contexto → analista → redactor → revisor → reglas y acción permitida del backend. Máximo cuatro llamadas LLM en el recorrido didáctico, profundidad 1, sin reintentos automáticos. En consulta web: máximo una llamada LLM.
