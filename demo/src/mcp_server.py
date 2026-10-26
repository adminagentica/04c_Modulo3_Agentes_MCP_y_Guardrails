"""Servidor MCP Python oficial: stdio o montado por gateway.py en Streamable HTTP."""
from mcp.server.fastmcp import FastMCP
from customer_service import CustomerService, email_address
from cobranza import tool_call
from codex_client import consultar_flujo


def create_mcp(service,profile='full'):
    mcp = FastMCP('Agentica Cobranza Python', stateless_http=True, json_response=True,
                  host='127.0.0.1', streamable_http_path='/mcp')

    @mcp.tool()
    def consultar_orquestador(pregunta: str, dni_seleccionado: str, conversation_id: str = "", draft_id: str = "") -> dict:
        """Consulta el MISMO workflow n8n de la app. dni_seleccionado es el contexto elegido por el usuario: no inferirlo ni cambiarlo para ajustarlo al DNI de la pregunta; vacío solo para políticas sin cliente. Los guardrails se aplican en n8n. Conserva conversation_id de la respuesta para turnos siguientes y draft.id como draft_id para confirmar ese borrador exacto. Puede preparar un borrador y ENVIAR por Gmail solo con confirmación explícita del operador después de mostrarlo. No inventes esa confirmación. Las consultas válidas usan OpenAI y pueden consumir crédito; no hacer pruebas de pago."""
        return consultar_flujo(pregunta,dni_seleccionado,conversation_id,draft_id)

    # Codex accede solo a la orquestación, sin herramientas directas que eviten ese recorrido.
    if profile=='codex':
        return mcp

    @mcp.tool()
    def consultar_saldo_ejecutivo(dni: str) -> dict:
        """Consulta exacta de un cliente sintético para el ejecutivo autorizado. No usa RAG para cifras."""
        return service.balance(dni)

    @mcp.tool()
    def validar_correo_dni(correo: str, dni: str) -> dict:
        """Compara correo y DNI con el registro. No verifica RENIEC ni acredita identidad fuerte."""
        try:
            account = service.balance(dni)
            if account['email'] != email_address(correo):
                raise ValueError('Sin coincidencia')
            return {'matched': True, 'case_id': account['case_id']}
        except ValueError:
            return {'matched': False}

    @mcp.tool()
    def consultar_politicas(pregunta: str) -> dict:
        """Consulta el RAG local existente; devuelve citas vigentes y se abstiene sin evidencia."""
        return service.policies(pregunta)

    @mcp.tool()
    def consultar_memoria(tenant_id: str, case_id: str) -> dict:
        """Recupera memoria del ámbito exacto; nunca permite alterar políticas."""
        return {'events': service.store.memory(tenant_id, case_id)}

    @mcp.tool()
    def consultar_caso(tenant_id: str, case_id: str) -> dict:
        """Lee hechos operativos del caso, excluyendo destinatario."""
        return tool_call(service.store, 'consultar_caso', {'tenant_id': tenant_id, 'case_id': case_id})

    @mcp.tool()
    def evaluar_reglas(tenant_id: str, case_id: str) -> dict:
        """Reutiliza el motor determinista de elegibilidad del orquestador."""
        return tool_call(service.store,'evaluar_reglas',{'tenant_id':tenant_id,'case_id':case_id})

    @mcp.tool()
    def consultar_politicas_rag(tenant_id: str, case_id: str) -> dict:
        """Compatibilidad con el orquestador anterior: consulta documental fija y validada."""
        return tool_call(service.store,'consultar_politicas_rag',{'tenant_id':tenant_id,'case_id':case_id})

    return mcp


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--profile',choices=['full','codex'],default='full')
    args=parser.parse_args()
    create_mcp(None if args.profile=='codex' else CustomerService(),args.profile).run(transport='stdio')
