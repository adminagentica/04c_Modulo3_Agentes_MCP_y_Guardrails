# Instrucciones del proyecto para Codex

## Misión y alcance
Mantener y explicar la demo de cobranza de la clase. Lee README.md y docs/01_ARQUITECTURA.md antes de cambiar código. La versión actual es 0.8.1. Las instrucciones de cada rol están en agents/. No conviertas estos archivos descriptivos en agentes en ejecución sin configurar el host correspondiente.

## Reglas obligatorias
- Todos los datos incluidos son sintéticos. No incorporar información real de clientes.
- No ejecutar pruebas que consuman saldo OpenAI, ni consultas positivas al webhook real, ni `codex exec`/Claude como parte de tests. Usar scripts/verificar.py y mocks.
- No leer, copiar, imprimir, exportar o publicar credenciales de n8n, claves API, tokens internos, cookies ni bases del docente.
- La app y el perfil MCP de consulta utilizan el mismo webhook n8n. No agregar un camino alternativo de saldo que evite sus validaciones.
- En el chat del ejecutivo, el DNI explícito de la pregunta establece el cliente activo; sin DNI se conserva el de la conversación. Dos DNI requieren aclaración. Cambiar de cliente invalida borradores pendientes. Por Gmail se sigue exigiendo correo registrado + DNI.
- SQL es la fuente de montos. El RAG solo aporta documentación vigente y autorizada, con citas verificables.
- Una consulta de saldo y recordatorio prepara y muestra un borrador local si el caso y las políticas validan. Solo la confirmación explícita del operador del borrador mostrado permite enviarlo en una consulta posterior, mediante el mismo workflow n8n. Nunca inventar una confirmación ni enviar durante pruebas.
- No habilitar envíos a nuevos destinatarios ni cambiar las reglas de contacto para obtener una prueba exitosa.
- La memoria de caso guarda eventos validados. La memoria de conversación conserva 20 turnos durante 30 días y vincula el borrador mostrado a la confirmación; no modifica permisos o reglas.
- No ejecutar importaciones sobre el n8n del docente ni iniciar servicios en puertos ocupados sin revisar el efecto.
- No realizar pushes forzados ni reemplazar archivos del repositorio ajenos a la tarea.

- La derivación humana pausa contactos del caso. El LLM no puede tomar ni resolver tickets, aprobar envíos o reanudar procesos por iniciativa propia. Hace falta una decisión explícita del operador autorizado; los tests de cierre usan solo tickets temporales.

## Trabajo y pruebas
Usar Python para MCP/gateway y Node para el RAG existente. Mantener la orquestación común de docs/01_ARQUITECTURA.md, con herramientas acotadas por rol/canal. El registro principal es demo/config/team.json; el motor de cuatro roles de config/agents.json es histórico. Revisar los casos de evals/casos.jsonl para cambios en comportamiento. Ejecutar scripts/verificar.py con el entorno Python instalado. Las pruebas no requieren credenciales reales.

## Respuesta al usuario
Responder en español. Indicar qué cambió, qué se verificó y qué falta. Conservar estados, referencias de ejecución y fuentes. No afirmar un envío, una aprobación documental o una prueba con modelo real que no ocurrió.

Ver [clientes y citas](docs/11_CASOS_Y_CITAS.md) y [RAG con OpenAI](docs/12_RAG_OPENAI.md).

Ver [borrador y confirmación](docs/13_BORRADOR_Y_CONFIRMACION.md).

El cliente activo del chat se establece por el DNI de la pregunta, sin selector obligatorio. Cambiarlo invalida borradores pendientes; nunca reutilizar un borrador de otro cliente.

## Agente de revisión de guardrails

Ante una petición explícita de usar guardrails, aplicar agents/guardrails.md y el catálogo demo/config/guardrails-reglas.json. El rol solo revisa código y evidencia suministrada; no ejecutar consultas pagadas, webhooks, correos, cambios de estado ni subdelegaciones. No confundir su dictamen con aprobación del operador o validación del backend. Ver docs/14_AGENTE_GUARDRAILS.md.
