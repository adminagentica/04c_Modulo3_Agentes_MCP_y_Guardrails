# MCP Python del equipo

El perfil público de consulta expone consultar_orquestador y conecta app/Codex/Claude con n8n. El supervisor usa además un cliente/servidor MCP interno del SDK oficial con transporte en memoria y capacidades separadas por canal. Ver [arquitectura](../../docs/01_ARQUITECTURA.md) y [contrato del supervisor](../../agents/orquestador.md).

El canal de consulta no expone herramientas de correo. La reserva y confirmación se limitan al gestor de correo; el envío físico sigue en n8n. No se entregan credenciales OpenAI a los clientes ni a los subagentes.
