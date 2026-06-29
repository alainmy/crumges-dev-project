from odoo import models, fields

class Project(models.Model):
    _inherit = 'project.project'

    use_approval_requirements = fields.Boolean(
        string='Enable Approval Requirements',
        help='Activate the customer approval workflow for tasks in this project.'
    )
    approval_default_content_type = fields.Selection([
        ('images', 'Images and Details (Approval Requirements)'),
        ('description', 'Task Description'),
        ('both', 'Both (Description and Images)')
    ], string='Default Approval Requirement Content', default='images', help="Choose what content will be sent by default to customers in the tasks of this project.")
    approval_default_note = fields.Text(
        string='Default Customer Notes',
        help="Default notes pre-filled into new tasks for approval requirements."
    )
    approval_conformity_text = fields.Text(
        string='Conformity Declaration',
        help="e.g. I declare I have reviewed each proof and they are correct..."
    )
    approval_force_login = fields.Boolean(
        string='Force Signer Login',
        help="Require customers to log in to approve proofs."
    )
    approval_expiration_days = fields.Integer(
        string='Timeout Days',
        help="Number of days before the proof automatically expires. Leave 0 to disable."
    )
    approval_expiration_action = fields.Selection([
        ('auto_approve', 'Auto-Approve (Silencio Positivo)'),
        ('auto_reject', 'Auto-Reject (Silencio Negativo)'),
        ('expire', 'Mark as Expired (Apply Rule)')
    ], string='Action on Expiration', default='auto_approve')
    approval_stage_rule_ids = fields.One2many(
        'project.approval.stage.rule',
        'project_id',
        string='Stage & State Rules'
    )
