# Verificación 0.8.0

- 148 pruebas Python aprobadas con conexiones TCP bloqueadas.
- 40 pruebas RAG aprobadas con modelos simulados.
- n8n aislado: borrador → confirmación → Gmail simulado → repetición sin duplicado, aprobado.
- App aislada: presentación del borrador, historial al recargar, confirmación y prevención de duplicado, aprobado.
- Runtime local: versión 0.8.0, RAG ready; ejecución 29 rechaza DNI contradictorio sin invocar modelo.
- Cero llamadas pagadas y cero correos reales enviados durante la preparación.

No se ha ejecutado una entrega Gmail real para probar esta versión. El próximo «Envíalo» del operador sobre un borrador válido sí activará el nodo Gmail real. El envío confirmado no añade otra llamada OpenAI.

Los 2091 tokens de la ejecución 25 corresponden a la prueba real anterior realizada por el usuario. No representan consumo de estas verificaciones.
