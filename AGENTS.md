# Instrucciones del proyecto para Codex

## Misión y alcance
Mantener y explicar la demo de cobranza de la clase. Lee README.md y docs/01_ARQUITECTURA.md antes de cambiar código. La versión actual es 0.5.0. Las instrucciones de cada rol están en agents/. No conviertas estos archivos descriptivos en agentes en ejecución sin configurar el host correspondiente.

## Reglas obligatorias
- Todos los datos incluidos son sintéticos. No incorporar información real de clientes.
- No ejecutar pruebas que consuman saldo OpenAI, ni consultas positivas al webhook real, ni `codex exec`/Claude como parte de tests. Usar scripts/verificar.py y mocks.
- No leer, copiar, imprimir, exportar o publicar credenciales de n8n, claves API, tokens internos, cookies ni bases del docente.
- La app y el perfil MCP de consulta utilizan el mismo webhook n8n. No agregar un camino alternativo de saldo que evite sus validaciones.
- El DNI seleccionado es un contexto independiente. Nunca inferirlo ni modificarlo para hacerlo coincidir con el DNI escrito en la pregunta.
- SQL es la fuente de montos. El RAG solo aporta documentación vigente y autorizada, con citas verificables.
- Una consulta sobre si se puede enviar un recordatorio solo evalúa condiciones; no autoriza ni ejecuta un correo. La app actual no ofrece envío de recordatorios.
- No habilitar envíos a nuevos destinatarios ni cambiar las reglas de contacto para obtener una prueba exitosa.
- La memoria es un registro acotado de eventos validados; no puede modificar permisos o reglas.
- No ejecutar importaciones sobre el n8n del docente ni iniciar servicios en puertos ocupados sin revisar el efecto.
- No realizar pushes forzados ni reemplazar archivos del repositorio ajenos a la tarea.

## Trabajo y pruebas
Usar Python para MCP/gateway y Node para el RAG existente. Mantener la orquestación común de docs/01_ARQUITECTURA.md, con herramientas acotadas por rol/canal. El registro principal es demo/config/team.json; el motor de cuatro roles de config/agents.json es histórico. Revisar los casos de evals/casos.jsonl para cambios en comportamiento. Ejecutar scripts/verificar.py con el entorno Python instalado. Las pruebas no requieren credenciales reales.

## Respuesta al usuario
Responder en español. Indicar qué cambió, qué se verificó y qué falta. Conservar estados, referencias de ejecución y fuentes. No afirmar un envío, una aprobación documental o una prueba con modelo real que no ocurrió.
