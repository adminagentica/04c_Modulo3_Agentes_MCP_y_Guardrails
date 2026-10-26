"""Coordinación del gestor de correo: n8n reserva, envía y devuelve el resultado."""
from agent_team import AgentSupervisor
from conversation_memory import ConversationMemory
from rag_client import validate_bundle
from reminder_actions import ReminderActions

class ReminderOrchestrator:
    def __init__(self,service):self.service=service
    def claim(self,conversation_id,request_id,draft_id):
        team=AgentSupervisor(self.service,request_id,None,validate_bundle)
        try:
            result=team.reminder_action('reclamar_recordatorio',{'conversation_id':conversation_id,'request_id':request_id,'draft_id':draft_id},'gestor_correo')
            return {**result,'should_send':True}
        except ValueError:
            draft=ReminderActions(self.service,validate_bundle).pending(conversation_id)
            if draft and draft['id']==draft_id and draft['state'] in {'sending','sent'}:
                return {'should_send':False,'state':'processing','answer':'El envío ya fue reservado o completado. No se repetirá.','conversation_id':conversation_id,'orchestrated_by':'n8n','citations':[],'model':'no-invocado'}
            with self.service.store.connect() as c:
                c.execute("UPDATE reminder_drafts SET state='blocked' WHERE id=? AND conversation_id=? AND state='approved'",(draft_id,conversation_id))
            result=team.finish({'state':'needs_review','handoff_reason':'regla_contacto','answer':'No se envió: cambió un dato, la política o un control antes de reservar. Revisa el caso y prepara otro borrador.','conversation_id':conversation_id,'orchestrated_by':'n8n','citations':[],'model':'no-invocado'})
            ConversationMemory(self.service.store).add(conversation_id,request_id,'assistant',result['answer'],result)
            return {**result,'should_send':False}
    def result(self,conversation_id,request_id,draft_id,gmail_id,execution_id):
        team=AgentSupervisor(self.service,request_id,None,validate_bundle)
        result=team.reminder_action('registrar_recordatorio',{'conversation_id':conversation_id,'request_id':request_id,'draft_id':draft_id,'gmail_id':gmail_id},'gestor_correo')
        result['execution_id']=str(execution_id);result['workflow_id']='agentica-orquestador-rag'
        result=team.finish(result)
        ConversationMemory(self.service.store).add(conversation_id,request_id,'assistant',result['answer'],result)
        return result
