# Clientes y citas de la demo 0.7.0

| DNI sintético | Saldo inicial | Escenario | Resultado esperado |
|---|---|---|---|
| 71425836 | PEN 850.00 | 5 días de atraso, consentimiento, correo de prueba autorizado, historial/promesas comprobados y sin señales de excepción | Puede prepararse un borrador sujeto a revisión y aprobación antes de enviar |
| 72536914 | PEN 1200.00 | 7 días de atraso y pago pendiente de conciliación | Pausa antes del LLM y derivación humana; POL-PAG-02 §4 |

Los cuatro clientes de config/demo-customers.json son sintéticos y usan la cuenta autorizada contacto@agentica.com.pe para autoenvíos de prueba. seed agrega registros que no existen y preserva cambios previos. El vencimiento relativo se calcula solo al crear cada caso. Los controles se guardan en inquiry_contact_controls: verificaciones de historial/promesas, pago pendiente, promesa incumplida, atención especial y canal autorizado.

El cliente apto cumple los controles operativos; **no equivale a correo enviado o aprobación humana registrada**. La app sigue consultando/preparando, sin una acción de envío de recordatorios. La respuesta de deuda por Gmail puede probarse con el asunto existente y «Mi DNI es 71425836», solo cuando el docente decida realizar el autoenvío. No se envió ningún correo durante esta preparación.

## Preguntas para clase

Seleccionar 71425836 y preguntar «¿Cuál es el saldo y puedo preparar un recordatorio de pago?». La pregunta positiva puede consumir OpenAI. Seleccionar 72536914 para demostrar el bloqueo; esa ruta no invoca el LLM, pero sí puede recuperar fuentes con embeddings locales y registrar una derivación.

## Revisión de la ejecución real 25

La prueba realizada por el usuario consumió 2091 tokens (1450 entrada, 641 salida) con gpt-5.4-mini-2026-03-17. Se conserva su metadato en evals/manual/ejecucion25.json; no fue una prueba automatizada del asistente.

Las referencias [3][5][4][1][2] pertenecían a cinco secciones de la misma POL-COB-04 v4:

- §3 y §5: condiciones de contacto y límites del borrador/revisión humana; pertinentes a la decisión.
- §1: alcance repetido por §3/§5; redundante en una respuesta breve.
- §4: límite de propuestas/descuentos; secundario para un simple recordatorio.
- §2: comprobaciones previas, no una autorización. Era necesario comprobar esos datos, no solamente citar la lista.
- §6 y §7: canal/trazabilidad y excepciones, relevantes antes de concluir que el caso puede continuar.

## Mejoras

La consulta de contacto prioriza §3, §5 y §6 para el caso apto. El modelo recibe como máximo tres secciones y debe responder de forma breve; solo se muestran enlaces realmente usados en el texto. Las excepciones se verifican en datos operativos. Para un pago pendiente, el bloqueo devuelve la cita específica POL-PAG-02 §4, sin pedir al LLM que vuelva a decidir.

IDs y hashes correctos no garantizan apoyo semántico: la revisión humana y las Evals siguen siendo necesarias. No se afirma una mejora de calidad medida con otro ensayo real: no se repitió la consulta usando saldo.
