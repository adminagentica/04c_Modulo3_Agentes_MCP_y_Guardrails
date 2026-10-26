"""Cliente de consultas para Codex: mismo webhook n8n que usa la app web."""
import argparse
import json
import os
from pathlib import Path
import re
from web_orchestration import ask_n8n


def consultar_flujo(pregunta: str, dni_seleccionado: str = '', conversation_id: str = '', draft_id: str = '') -> dict:
    if not isinstance(pregunta,str) or not 3<=len(pregunta.strip())<=1000:
        raise ValueError('Pregunta inválida')
    if dni_seleccionado and not re.fullmatch('[0-9]{8}',dni_seleccionado):
        raise ValueError('DNI seleccionado inválido')
    token=os.getenv('COBRANZA_TOKEN','')
    if not token:
        token=(Path(__file__).resolve().parents[1]/'data/gateway.token').read_text().strip()
    return ask_n8n(pregunta,dni_seleccionado,token,conversation_id,draft_id) if draft_id else ask_n8n(pregunta,dni_seleccionado,token,conversation_id) if conversation_id else ask_n8n(pregunta,dni_seleccionado,token)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('pregunta');p.add_argument('--dni',default='');p.add_argument('--conversation',default='');p.add_argument('--draft',default='')
    args=p.parse_args()
    print(json.dumps(consultar_flujo(args.pregunta,args.dni,args.conversation,args.draft),ensure_ascii=False,indent=2))
