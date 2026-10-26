# Clientes y citas de la demo 0.8.1

| DNI sintético | Saldo inicial | Escenario | Resultado esperado |
|---|---|---|---|
| 71425836 | PEN 850.00 | 5 días de atraso, consentimiento, correo de prueba autorizado, historial/promesas comprobados y sin señales de excepción | Puede prepararse un borrador sujeto a revisión y aprobación antes de enviar |
| 72536914 | PEN 1200.00 | 7 días de atraso y pago pendiente de conciliación | Pausa antes del LLM y derivación humana; POL-PAG-02 §4 |
| 73148265 | PEN 640.00 | 5 días de atraso; controles comprobados y sin excepciones | Preparar borrador y enviar solo tras «Envíalo» |
| 74259316 | PEN 2150.00 | 8 días de atraso; controles comprobados y sin excepciones | Preparar borrador y enviar solo tras «Envíalo» |
| 75361428 | PEN 980.00 | 6 días de atraso; pago pendiente de conciliación | Bloqueo y derivación humana; POL-PAG-02 §4 |
| 76482539 | PEN 1740.00 | 9 días de atraso; pago pendiente de conciliación | Bloqueo y derivación humana; POL-PAG-02 §4 |

Los ocho clientes de config/demo-customers.json son sintéticos y usan la cuenta autorizada contacto@agentica.com.pe para autoenvíos de prueba. seed agrega registros que no existen y preserva cambios previos. El vencimiento relativo se calcula solo al crear cada caso. Los controles se guardan en inquiry_contact_controls: verificaciones de historial/promesas, pago pendiente, promesa incumplida, atención especial y canal autorizado.

El cliente apto cumple los controles operativos; **no equivale a correo enviado o aprobación humana registrada**. La app prepara un borrador completo; solo una confirmación explícita posterior permite enviarlo por n8n. La respuesta de deuda por Gmail puede probarse con el asunto existente y «Mi DNI es 71425836», solo cuando el docente decida realizar el autoenvío. No se envió ningún correo durante esta preparación.

## Preguntas para clase

Preguntar «¿Cuál es el saldo de 71425836 y puedo preparar un recordatorio de pago?» sin selección previa. La pregunta positiva puede consumir OpenAI. Escribir el DNI 72536914 para demostrar el bloqueo; esa ruta no invoca el LLM, pero sí puede recuperar fuentes con embeddings locales y registrar una derivación.

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

## Alternar demostraciones

Para recordatorios, alterna 71425836, 73148265 y 74259316. Cada uno tiene factura propia, por lo que un envío previo de otro cliente no consume su reserva. Para bloqueos con derivación humana, alterna 72536914, 75361428 y 76482539. Los nuevos casos bloqueados tienen un pago pendiente de conciliación, por lo que no se debe contactar hasta revisar. No se borran envíos ni tickets existentes para repetir la clase. Las fechas de vencimiento se fijan al crear los registros; al pasar más de 30 días dejarán de cumplir gestión temprana.
