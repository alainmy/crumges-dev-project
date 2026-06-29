from odoo import models, fields

class ProjectApprovalStageRule(models.Model):
    _name = 'project.approval.stage.rule'
    _description = 'Project Approval Requirement Stage Rule'
    _order = 'approval_status'

    project_id = fields.Many2one('project.project', string='Project', ondelete='cascade', required=True)
    approval_status = fields.Selection([
        ('sent', '🟡 Sent for Approval'),
        ('approved', '🟢 Approved'),
        ('rejected', '🟠 Revisar'),
        ('discontinued', '🔴 Cancelado / Descontinuado'),
        ('expired', '🟣 Expired (Timeout)')
    ], string='Approval Status', required=True)
    stage_id = fields.Many2one('project.task.type', string='Stage', required=True)
    task_state = fields.Selection([
        ('01_in_progress', 'In Progress'),
        ('02_changes_requested', 'Changes Requested'),
        ('03_approved', 'Approved'),
        ('04_waiting_normal', 'Waiting'),
        ('1_done', 'Done'),
        ('1_canceled', 'Canceled')
    ], string='Task State', required=True)
    task_state_icon = fields.Selection(related='task_state', string=" ")

    _sql_constraints = [
        ('project_status_uniq', 'unique(project_id, approval_status)', 'A project can only have one rule per proof status.')
    ]
