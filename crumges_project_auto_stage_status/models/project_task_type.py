from odoo import fields, models


class ProjectTaskType(models.Model):
    _inherit = 'project.task.type'

    def _get_default_state_selection(self):
        return self.env['project.task']._fields['state'].selection

    default_state = fields.Selection(
        selection=_get_default_state_selection,
        string='Default Status',
        help='When a task enters this stage, its status will automatically be updated to this value.'
    )

    force_state_readonly = fields.Boolean(
        string='Forzar Estado (Solo Lectura)',
        default=False,
        help='Si está activo, los usuarios no podrán cambiar el estado de la tarea manualmente mientras esté en esta etapa.'
    )

    # Campo falso (dummy) requerido por el widget 'project_task_state_selection'
    # el cual espera que exista un project_id en el modelo donde se instancia.
    project_id = fields.Many2one(
        'project.project',
        compute='_compute_dummy_project_id',
        store=False,
        string="Dummy Project (For Widget)"
    )

    def _compute_dummy_project_id(self):
        for rec in self:
            rec.project_id = False
