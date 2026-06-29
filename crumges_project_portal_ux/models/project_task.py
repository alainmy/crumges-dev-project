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

    def action_send_mail_ux(self):
        self.ensure_one()
        template = self.env.ref('crumges_project_portal_ux.email_template_project_task', raise_if_not_found=False)
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': {
                'default_model': 'project.task',
                'default_res_ids': self.ids,
                'default_template_id': template.id if template else False,
                'default_composition_mode': 'comment',
                'default_email_layout_xmlid': 'mail.mail_notification_layout_with_responsible_signature',
                'force_email': True,
            },
        }
