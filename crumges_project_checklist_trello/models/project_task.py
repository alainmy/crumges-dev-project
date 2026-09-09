# -*- coding: utf-8 -*-
from odoo import api, models, fields

class ProjectTask(models.Model):
    _inherit = 'project.task'

    checklist_line_ids = fields.One2many('project.task.checklist.line', 'task_id', string='Checklists')

    trello_checklist_summary = fields.Char(string="Progreso Checklists", compute="_compute_trello_checklist_summary", store=False)

    @api.depends('checklist_line_ids.is_checked', 'checklist_line_ids.display_type')
    def _compute_trello_checklist_summary(self):
        for task in self:
            items = task.checklist_line_ids.filtered(lambda l: not l.display_type)
            total = len(items)
            if total > 0:
                checked = len(items.filtered(lambda l: l.is_checked))
                task.trello_checklist_summary = f"{checked}/{total}"
            else:
                task.trello_checklist_summary = ""

    def action_add_checklist(self):
        self.ensure_one()
        return {
            'name': 'Añadir Checklist',
            'type': 'ir.actions.act_window',
            'res_model': 'project.task.checklist.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_task_id': self.id}
        }

    def _sync_checklists_to_trello(self):
        self.ensure_one()
        if not self.trello_card_id:
            return
            
        user = self.env.user if self.env.user.trello_token else self.env['res.users'].sudo().search([('trello_token', '!=', False)], limit=1)
        if not user:
            return
            
        current_trello_checklist_id = None
        
        for line in self.checklist_line_ids:
            if line.display_type == 'line_section':
                # Es un título de checklist
                if not line.trello_checklist_id:
                    res = user._trello_request('POST', f'/cards/{self.trello_card_id}/checklists', params={'name': line.name})
                    if res and res.get('id'):
                        line.with_context(trello_webhook_sync=True).write({'trello_checklist_id': res['id']})
                        current_trello_checklist_id = res['id']
                else:
                    user._trello_request('PUT', f'/checklists/{line.trello_checklist_id}', params={'name': line.name})
                    current_trello_checklist_id = line.trello_checklist_id
            
            elif not line.display_type:
                # Es un ítem
                if current_trello_checklist_id:
                    if not line.trello_item_id:
                        res = user._trello_request('POST', f'/checklists/{current_trello_checklist_id}/checkItems', params={'name': line.name, 'checked': 'true' if line.is_checked else 'false'})
                        if res and res.get('id'):
                            line.with_context(trello_webhook_sync=True).write({'trello_item_id': res['id']})
                    else:
                        state = 'complete' if line.is_checked else 'incomplete'
                        user._trello_request('PUT', f'/cards/{self.trello_card_id}/checklist/{current_trello_checklist_id}/checkItem/{line.trello_item_id}', params={'name': line.name, 'state': state})

    def _delete_trello_checklist(self, trello_checklist_id):
        user = self.env.user if self.env.user.trello_token else self.sudo().search([('trello_token', '!=', False)], limit=1)
        if user and trello_checklist_id:
            user._trello_request('DELETE', f'/checklists/{trello_checklist_id}')

    def _delete_trello_checkitem(self, trello_checklist_id, trello_item_id):
        user = self.env.user if self.env.user.trello_token else self.sudo().search([('trello_token', '!=', False)], limit=1)
        if user and trello_checklist_id and trello_item_id:
            user._trello_request('DELETE', f'/checklists/{trello_checklist_id}/checkItems/{trello_item_id}')

