# -*- coding: utf-8 -*-
from odoo import models, fields

class ChecklistWizard(models.TransientModel):
    _name = 'project.task.checklist.wizard'
    _description = 'Wizard para añadir Checklist'

    name = fields.Char(string='Título', required=True, default='Checklist')
    task_id = fields.Many2one('project.task', string='Task', required=True)
    is_copy = fields.Boolean(string='Copiar desde un checklist existente', default=False)
    copy_from_id = fields.Many2one('project.task.checklist', string='Copiar elementos desde...')

    def action_create_checklist(self):
        self.ensure_one()
        new_checklist = self.env['project.task.checklist'].create({
            'name': self.name,
            'task_id': self.task_id.id,
        })
        if self.is_copy and self.copy_from_id:
            for item in self.copy_from_id.item_ids:
                self.env['project.task.checklist.item'].create({
                    'name': item.name,
                    'checklist_id': new_checklist.id,
                    # We don't copy Trello IDs because this is a new checklist
                })
        return {'type': 'ir.actions.act_window_close'}
