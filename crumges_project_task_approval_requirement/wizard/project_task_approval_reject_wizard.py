from odoo import models, fields, api

class ProjectTaskApprovalRejectWizard(models.TransientModel):
    _name = 'project.task.approval.reject.wizard'
    _description = 'Task Approval Revision Wizard'

    reason = fields.Text(string="Motivo de la Revisión", required=True)

    def action_reject(self):
        active_id = self.env.context.get('active_id')
        if active_id:
            task = self.env['project.task'].browse(active_id)
            task.write({
                'approval_status': 'rejected',
                'approval_rejection_reason': self.reason
            })
        return {'type': 'ir.actions.act_window_close'}
