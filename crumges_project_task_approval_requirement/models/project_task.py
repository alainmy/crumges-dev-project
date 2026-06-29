from odoo import models, fields, api, _
from odoo.exceptions import UserError
import uuid
from datetime import timedelta

class ProjectTask(models.Model):
    _inherit = 'project.task'

    use_approval_requirements = fields.Boolean(related='project_id.use_approval_requirements')
    require_approval = fields.Boolean(string='Requires Approval Requirement', default=False)
    approval_line_ids = fields.One2many('project.approval.requirement.line', 'task_id', string='Approval Requirements')
    approval_content_type = fields.Selection([
        ('images', 'Images and Details (Approval Requirements)'),
        ('description', 'Task Description'),
        ('both', 'Both (Description and Images)')
    ], string='Content to Approve', default='images')
    approval_note = fields.Text(string='Customer Notes', compute='_compute_approval_texts', store=True, readonly=False)
    approval_conformity_text = fields.Text(string='Conformity Declaration', compute='_compute_approval_texts', store=True, readonly=False)
    approval_status = fields.Selection([
        ('draft', '⚪ Draft'),
        ('sent', '🟡 Sent for Approval'),
        ('approved', '🟢 Approved'),
        ('rejected', '🟠 Revisar'),
        ('discontinued', '🔴 Cancelado / Descontinuado'),
        ('expired', '🟣 Expired')
    ], string='Approval Status', default='draft', tracking=True, copy=False)
    approval_token = fields.Char(string='Access Token', default=lambda s: str(uuid.uuid4()), copy=False)
    approval_sent_date = fields.Datetime(string='Sent Date', copy=False)
    
    is_approval_signed = fields.Boolean(string='Is Signed', compute='_compute_is_approval_signed', store=True)
    approval_signature = fields.Image(string='Customer Signature', copy=False)
    approval_signed_by = fields.Char(string='Signed By', copy=False)
    approval_signed_date = fields.Datetime(string='Signed Date', copy=False)
    approval_rejection_reason = fields.Text(string='Rejection Reason', copy=False)

    @api.depends('approval_signature')
    def _compute_is_approval_signed(self):
        for task in self:
            task.is_approval_signed = bool(task.approval_signature)

    @api.depends('project_id.approval_default_note', 'project_id.approval_conformity_text', 'project_id.approval_default_content_type')
    def _compute_approval_texts(self):
        for task in self:
            if task.project_id:
                task.approval_content_type = task.project_id.approval_default_content_type or 'images'
                task.approval_note = task.project_id.approval_default_note or False
                task.approval_conformity_text = task.project_id.approval_conformity_text or False
            else:
                if not task.approval_content_type:
                    task.approval_content_type = 'images'

    def _get_first_available_stage(self):
        """Returns the first available stage that is not protected by approval rules for this task's project."""
        self.ensure_one()
        protected_stages = self.project_id.approval_stage_rule_ids.mapped('stage_id.id') if self.project_id else []
        domain = [('id', 'not in', protected_stages)]
        
        project_stages = self.env['project.task.type'].browse()
        if self.project_id:
            project_stages = self.env['project.task.type'].search([('project_ids', 'in', self.project_id.id)] + domain, order='sequence asc')
        if not project_stages:
            project_stages = self.env['project.task.type'].search(domain, order='sequence asc')
            
        return project_stages[0] if project_stages else False

    def copy(self, default=None):
        if default is None:
            default = {}
            
        if self.use_approval_requirements and self.require_approval:
            first_stage = self._get_first_available_stage()
            if first_stage:
                default['stage_id'] = first_stage.id

        return super(ProjectTask, self).copy(default)

    def write(self, vals):
        if 'stage_id' in vals and not self.env.context.get('ignore_approval_stage_check'):
            for task in self:
                if task.use_approval_requirements and task.require_approval:
                    protected_stages = task.project_id.approval_stage_rule_ids.mapped('stage_id.id')
                    
                    if vals['stage_id'] in protected_stages and task.stage_id.id != vals['stage_id']:
                        raise UserError(_("No puedes mover manualmente la tarea a esta etapa. El ciclo de vida de aprobación es gestionado automáticamente por el sistema."))
                    
                    sent_rule = task.project_id.approval_stage_rule_ids.filtered(lambda r: r.approval_status == 'sent')
                    if sent_rule and task.stage_id.id == sent_rule[0].stage_id.id and task.stage_id.id != vals['stage_id']:
                        raise UserError(_("No puedes mover manualmente la tarea fuera de la etapa de 'Enviado para Aprobación'. Debes esperar la respuesta del cliente o cancelar la solicitud."))
                        
        # Detect state changes before write for notifications
        tasks_activated = self.env['project.task']
        if 'require_approval' in vals and vals['require_approval']:
            for task in self:
                if task.use_approval_requirements and not task.require_approval:
                    tasks_activated |= task

        res = super().write(vals)

        # Notify activation
        if tasks_activated:
            template = self.env.ref('crumges_project_task_approval_requirement.mail_template_task_approval_required', raise_if_not_found=False)
            if template:
                for task in tasks_activated:
                    task.message_post_with_source(template, subtype_xmlid='mail.mt_comment')

        # Apply stage and state rules if approval_status changed
        if 'approval_status' in vals:
            for task in self:
                if task.use_approval_requirements:
                    # Notify status change
                    template = False
                    if vals['approval_status'] == 'sent':
                        template = self.env.ref('crumges_project_task_approval_requirement.mail_template_task_approval_sent', raise_if_not_found=False)
                    elif vals['approval_status'] == 'approved':
                        template = self.env.ref('crumges_project_task_approval_requirement.mail_template_task_approval_approved', raise_if_not_found=False)
                    elif vals['approval_status'] == 'rejected':
                        template = self.env.ref('crumges_project_task_approval_requirement.mail_template_task_approval_rejected', raise_if_not_found=False)
                    elif vals['approval_status'] == 'discontinued':
                        template = self.env.ref('crumges_project_task_approval_requirement.mail_template_task_approval_discontinued', raise_if_not_found=False)
                    
                    if template:
                        task.message_post_with_source(template, subtype_xmlid='mail.mt_comment')

                    rule = task.project_id.approval_stage_rule_ids.filtered(lambda r: r.approval_status == vals['approval_status'])
                    if rule:
                        update_vals = {}
                        if rule[0].stage_id and task.stage_id.id != rule[0].stage_id.id:
                            update_vals['stage_id'] = rule[0].stage_id.id
                        if rule[0].task_state and getattr(task, 'state', False) != rule[0].task_state:
                            update_vals['state'] = rule[0].task_state
                        if update_vals:
                            task.with_context(ignore_approval_stage_check=True).write(update_vals)
        return res

    def action_send_approval_requirement(self):
        self.ensure_one()
        self._generate_approval_token()
        self.approval_sent_date = fields.Datetime.now()
        # Updating approval_status will automatically trigger the rule logic in write()
        self.approval_status = 'sent'
        
    def action_reset_approval(self):
        self.ensure_one()
        vals = {
            'approval_status': 'draft',
            'approval_rejection_reason': False,
            'approval_sent_date': False,
            'approval_signed_by': False,
            'approval_signed_date': False,
            'approval_signature': False,
        }
        
        # Reset stage to the first available non-protected stage
        if self.use_approval_requirements and self.require_approval:
            first_stage = self._get_first_available_stage()
            if first_stage:
                vals['stage_id'] = first_stage.id
                
            # Also reset the state to standard (usually '01_in_progress' or False)
            vals['state'] = '01_in_progress'
            
        self.with_context(ignore_approval_stage_check=True).write(vals)

    def _generate_approval_token(self):
        for task in self:
            if not task.approval_token:
                task.approval_token = str(uuid.uuid4())

    @api.model
    def _cron_check_approval_expiration(self):
        tasks = self.search([('approval_status', '=', 'sent'), ('approval_sent_date', '!=', False)])
        for task in tasks:
            project = task.project_id
            if not project.approval_expiration_days:
                continue
            
            expiration_date = task.approval_sent_date + timedelta(days=project.approval_expiration_days)
            if fields.Datetime.now() >= expiration_date:
                action = project.approval_expiration_action
                if action == 'auto_approve':
                    task.write({
                        'approval_status': 'approved',
                        'approval_signed_by': 'Auto-approved by system (Expiration)',
                        'approval_signed_date': fields.Datetime.now()
                    })
                elif action == 'auto_reject':
                        task.write({
                            'approval_status': 'rejected',
                            'approval_rejection_reason': 'Auto-rejected (Revision Requested) due to response timeout.'
                        })
                elif action == 'expire':
                    task.write({
                        'approval_status': 'expired',
                        'approval_rejection_reason': 'Expired (Timeout)'
                    })
