# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProjectTaskChecklist(models.Model):
    _name = 'project.task.checklist'
    _description = 'Task Checklist'
    _order = 'sequence, id'

    task_id = fields.Many2one('project.task', string='Task', required=True, ondelete='cascade', index=True)
    name = fields.Char(string='Name', required=True)
    identity_key = fields.Char(string='Identity Key', copy=False, index=True)
    sequence = fields.Integer(default=10)

    trello_checklist_id = fields.Char(string='Trello Checklist ID', copy=False, index=True)

    item_ids = fields.One2many('project.task.checklist.item', 'checklist_id', string='Items')

    section_progress = fields.Char(string="Progreso", compute="_compute_section_progress", store=False)

    @api.depends('item_ids.is_checked', 'item_ids.sequence')
    def _compute_section_progress(self):
        for checklist in self:
            total = len(checklist.item_ids)
            if total > 0:
                checked = len(checklist.item_ids.filtered(lambda i: i.is_checked))
                checklist.section_progress = f"({checked}/{total})"
            else:
                checklist.section_progress = "(0/0)"

    def action_view_checklist(self):
        self.ensure_one()
        return {
            'name': self.name,
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_task_id': self.task_id.id},
        }

    def action_delete_checklist(self):
        self.ensure_one()
        self.unlink()

    def action_clean_duplicate_checklists(self):
        self.ensure_one()
        if self.task_id:
            return self.task_id.action_clean_duplicate_checklists()
        return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {'title': 'Sin duplicados', 'message': 'No hay duplicados para limpiar en esta tarea.', 'type': 'info', 'sticky': False}}

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name') and not vals.get('identity_key'):
                vals['identity_key'] = (vals['name'] or '').strip().lower()
        records = super().create(vals_list)
        for rec in records:
            if rec.task_id.trello_card_id and not self._context.get('trello_webhook_sync'):
                rec.task_id.with_delay(channel='root.trello_sync')._sync_checklists_to_trello()
        return records

    def write(self, vals):
        if 'name' in vals:
            vals['identity_key'] = (vals.get('name') or self.name or '').strip().lower()
        res = super().write(vals)
        if self._context.get('trello_webhook_sync'):
            return res
        if any(f in vals for f in ['name', 'sequence']):
            for rec in self:
                if rec.task_id.trello_card_id:
                    rec.task_id.with_delay(channel='root.trello_sync')._sync_checklists_to_trello()
        return res

    def unlink(self):
        for rec in self:
            if not self._context.get('trello_webhook_sync') and rec.task_id.trello_card_id:
                if rec.trello_checklist_id:
                    rec.task_id.with_delay(channel='root.trello_sync')._delete_trello_checklist(rec.trello_checklist_id)
        return super().unlink()