# -*- coding: utf-8 -*-

from odoo import models

class ProjectTask(models.Model):
    _inherit = 'project.task'

    def _get_report_base_filename(self):
        self.ensure_one()
        return 'Tarea - %s' % (self.name)

    def action_preview_task(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': self.get_portal_url(),
        }
