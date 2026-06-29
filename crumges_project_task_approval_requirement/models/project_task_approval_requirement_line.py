from odoo import models, fields

class ProjectTaskApprovalRequirementLine(models.Model):
    _name = 'project.approval.requirement.line'
    _description = 'Approval Requirement Line'

    task_id = fields.Many2one('project.task', string='Task', required=True, ondelete='cascade')
    image = fields.Image('Approval Image', required=True)
    caption = fields.Text('Caption')
