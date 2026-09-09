# -*- coding: utf-8 -*-
from odoo import models, fields

class ChecklistWizard(models.TransientModel):
    _name = 'project.task.checklist.wizard'
    _description = 'Wizard para añadir Checklist'

    name = fields.Char(string='Título', required=True, default='Checklist')
    task_id = fields.Many2one('project.task', string='Task', required=True)
    is_copy = fields.Boolean(string='Copiar desde un checklist existente', default=False)
    copy_from_id = fields.Many2one('project.task.checklist.line', string='Copiar elementos desde...', domain="[('display_type', '=', 'line_section')]")

    def action_create_checklist(self):
        self.ensure_one()
        new_section = self.env['project.task.checklist.line'].create({
            'name': self.name,
            'task_id': self.task_id.id,
            'display_type': 'line_section'
        })
        if self.is_copy and self.copy_from_id:
            items_to_copy = self.copy_from_id._get_items()
            for item in items_to_copy:
                self.env['project.task.checklist.line'].create({
                    'name': item.name,
                    'task_id': self.task_id.id,
                    'is_checked': False,
                    # We don't copy Trello IDs because this is a new checklist
                })
        return {'type': 'ir.actions.act_window_close'}
