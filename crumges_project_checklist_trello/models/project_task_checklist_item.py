# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProjectTaskChecklistItem(models.Model):
    _name = 'project.task.checklist.item'
    _description = 'Task Checklist Item'
    _order = 'sequence, id'

    checklist_id = fields.Many2one('project.task.checklist', string='Checklist', required=True, ondelete='cascade', index=True)
    name = fields.Char(string='Name', required=True)
    identity_key = fields.Char(string='Identity Key', copy=False, index=True)
    sequence = fields.Integer(default=10)
    is_checked = fields.Boolean(string='Checked', default=False)

    trello_item_id = fields.Char(string='Trello Item ID', copy=False, index=True)

    def action_delete_item(self):
        self.ensure_one()
        self.unlink()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name') and not vals.get('identity_key'):
                vals['identity_key'] = (vals['name'] or '').strip().lower()
        records = super().create(vals_list)
        for rec in records:
            if rec.checklist_id.task_id.trello_card_id and not self._context.get('trello_webhook_sync'):
                rec.checklist_id.task_id.with_delay(channel='root.trello_sync')._sync_checklists_to_trello()
        return records

    def write(self, vals):
        if 'name' in vals:
            vals['identity_key'] = (vals.get('name') or self.name or '').strip().lower()
        res = super().write(vals)
        if self._context.get('trello_webhook_sync'):
            return res
        if any(f in vals for f in ['name', 'sequence', 'is_checked']):
            for rec in self:
                if rec.checklist_id.task_id.trello_card_id:
                    rec.checklist_id.task_id.with_delay(channel='root.trello_sync')._sync_checklists_to_trello()
        return res

    def unlink(self):
        for rec in self:
            if not self._context.get('trello_webhook_sync') and rec.checklist_id.task_id.trello_card_id:
                if rec.trello_item_id and rec.checklist_id.trello_checklist_id:
                    rec.checklist_id.task_id.with_delay(channel='root.trello_sync')._delete_trello_checkitem(
                        rec.checklist_id.trello_checklist_id, rec.trello_item_id)
        return super().unlink()

    def action_delete_item_task_safe(self):
        self.ensure_one()
        if self.checklist_id and self.checklist_id.task_id:
            return self.checklist_id.task_id.action_clean_duplicate_checklists()
        return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {'title': 'Sin duplicados', 'message': 'No hay ítems a limpiar.', 'type': 'info', 'sticky': False}}