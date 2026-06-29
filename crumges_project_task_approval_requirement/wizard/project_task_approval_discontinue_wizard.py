from odoo import models, fields

class ProjectTaskApprovalDiscontinueWizard(models.TransientModel):
    _name = 'project.task.approval.discontinue.wizard'
    _description = 'Task Approval Discontinue Wizard'

    reason = fields.Text(string="Motivo de Cancelación", required=True)

    def action_discontinue(self):
        active_id = self.env.context.get('active_id')
        if active_id:
            task = self.env['project.task'].browse(active_id)
            task.write({
                'approval_status': 'discontinued',
                'approval_rejection_reason': self.reason
            })
