# -*- coding: utf-8 -*-
from odoo import models

class ResUsers(models.Model):
    _inherit = 'res.users'

    def _process_trello_webhook_event(self, action_data):
        if action_data.get('appCreator'):
            return

        super()._process_trello_webhook_event(action_data)

        action_type = action_data.get('type')
        card_data = action_data.get('data', {}).get('card', {})
        
        # Odoo es el mandatario: bloqueamos creación/edición/eliminación desde Trello
        if action_type in ('addChecklistToCard', 'updateChecklist', 'removeChecklistFromCard', 'createCheckItem', 'deleteCheckItem', 'updateCheckItem'):
            
            # Evitar infinite loop: Si fue creado por Odoo, ya tenemos el ID, así que lo ignoramos
            if action_type == 'addChecklistToCard':
                if self.env['project.task.checklist'].sudo().search_count([('trello_checklist_id', '=', action_data.get('data', {}).get('checklist', {}).get('id'))]):
                    return
            if action_type == 'createCheckItem':
                if self.env['project.task.checklist.item'].sudo().search_count([('trello_item_id', '=', action_data.get('data', {}).get('checkItem', {}).get('id'))]):
                    return
                    
            # Evitar infinite loop: Si es un update pero no cambió el nombre (Trello no reporta 'old.name'), ignorar
            if action_type in ('updateChecklist', 'updateCheckItem'):
                if 'name' not in action_data.get('data', {}).get('old', {}):
                    # Solo nos importa si es un cambio de estado
                    if action_type == 'updateCheckItem' and 'state' in action_data.get('data', {}).get('checkItem', {}):
                        pass # Permitir cambio de estado
                    else:
                        return # No-op o cambio irrelevante, ignorar
            
            # updateCheckItem is also used for renaming an item.
            if action_type == 'updateCheckItem' and 'state' in action_data.get('data', {}).get('checkItem', {}) and 'name' not in action_data.get('data', {}).get('old', {}):
                # State change is allowed
                pass
            else:
                # We revert it by forcing a sync of the checklist from Odoo
                card_id = card_data.get('id')
                if card_id:
                    task = self.env['project.task'].sudo().search([('trello_card_id', '=', card_id)], limit=1)
                    if task:
                        # Si borraron algo en Trello, limpiamos los IDs en Odoo para forzar su recreación
                        if action_type == 'removeChecklistFromCard':
                            checklist_id = action_data.get('data', {}).get('checklist', {}).get('id')
                            if checklist_id:
                                checklist = task.checklist_ids.filtered(lambda c: c.trello_checklist_id == checklist_id)
                                if checklist:
                                    checklist.with_context(trello_webhook_sync=True).write({'trello_checklist_id': False})
                                    checklist.item_ids.with_context(trello_webhook_sync=True).write({'trello_item_id': False})
                        elif action_type == 'deleteCheckItem':
                            item_id = action_data.get('data', {}).get('checkItem', {}).get('id')
                            if item_id:
                                item = task.checklist_ids.item_ids.filtered(lambda i: i.trello_item_id == item_id)
                                if item:
                                    item.with_context(trello_webhook_sync=True).write({'trello_item_id': False})

                        # Mandar a sincronizar todos los checklists de esta tarea para revertir daños
                        task.with_delay(channel='root.trello_sync')._sync_checklists_to_trello()
                return

        # Sincronización de progreso (Trello -> Odoo)
        if action_type in ('updateCheckItemStateOnCard', 'updateCheckItem'):
            check_item_data = action_data.get('data', {}).get('checkItem', {})
            state = check_item_data.get('state')
            item_id = check_item_data.get('id')
            if item_id and state in ('complete', 'incomplete'):
                item = self.env['project.task.checklist.item'].sudo().search([('trello_item_id', '=', item_id)], limit=1)
                if item:
                    item.with_context(trello_webhook_sync=True).write({'is_checked': state == 'complete'})