# -*- coding: utf-8 -*-
from odoo import models

class ResUsers(models.Model):
    _inherit = 'res.users'

    def _process_trello_webhook_event(self, action_data):
        super()._process_trello_webhook_event(action_data)
        
        action_type = action_data.get('type')
        card_data = action_data.get('data', {}).get('card', {})
        
        # Odoo es el mandatario: bloqueamos creación/edición/eliminación desde Trello
        if action_type in ('addChecklistToCard', 'updateChecklist', 'removeChecklistFromCard', 'createCheckItem', 'deleteCheckItem', 'updateCheckItem'):
            # updateCheckItem is also used for renaming an item. Trello sends state changes as 'updateCheckItemStateOnCard' usually, or 'updateCheckItem' with 'state'.
            # If it's a state change, we allow it. If it's a rename or delete, we block it.
            if action_type == 'updateCheckItem' and 'state' in action_data.get('data', {}).get('checkItem', {}):
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
                                in_deleted_section = False
                                for line in task.checklist_line_ids:
                                    if line.display_type == 'line_section':
                                        if line.trello_checklist_id == checklist_id:
                                            line.trello_checklist_id = False
                                            in_deleted_section = True
                                        else:
                                            in_deleted_section = False
                                    elif in_deleted_section and not line.display_type:
                                        line.trello_item_id = False
                        elif action_type == 'deleteCheckItem':
                            item_id = action_data.get('data', {}).get('checkItem', {}).get('id')
                            if item_id:
                                item = task.checklist_line_ids.filtered(lambda l: l.trello_item_id == item_id)
                                if item:
                                    item.trello_item_id = False

                        # Mandar a sincronizar todos los checklists de esta tarea para revertir daños
                        task.with_delay(channel='root.trello_sync')._sync_checklists_to_trello()
                return

        # Sincronización de progreso (Trello -> Odoo)
        if action_type in ('updateCheckItemStateOnCard', 'updateCheckItem'):
            check_item_data = action_data.get('data', {}).get('checkItem', {})
            state = check_item_data.get('state')
            item_id = check_item_data.get('id')
            if item_id and state in ('complete', 'incomplete'):
                item = self.env['project.task.checklist.line'].sudo().search([('trello_item_id', '=', item_id)], limit=1)
                if item:
                    item.with_context(trello_webhook_sync=True).write({'is_checked': state == 'complete'})
