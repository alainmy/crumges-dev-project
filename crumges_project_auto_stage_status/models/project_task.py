from odoo import api, fields, models


class ProjectTask(models.Model):
    _inherit = 'project.task'

    stage_force_state_readonly = fields.Boolean(
        related='stage_id.force_state_readonly',
        string='Forzar Estado (Solo Lectura)',
        readonly=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'stage_id' in vals and 'state' not in vals:
                stage = self.env['project.task.type'].browse(vals['stage_id'])
                if stage.default_state:
                    vals['state'] = stage.default_state
        return super().create(vals_list)

    def write(self, vals):
        from odoo.exceptions import UserError

        # Validar si se está intentando cambiar el estado manualmente
        if 'state' in vals and not 'stage_id' in vals:
            for task in self:
                if task.stage_id.force_state_readonly and vals['state'] != task.state:
                    raise UserError(f'El estado de esta tarea es de solo lectura por configuración de su etapa ({task.stage_id.name}).')

        if 'stage_id' in vals and 'state' not in vals:
            stage = self.env['project.task.type'].browse(vals['stage_id'])
            if stage.default_state:
                vals['state'] = stage.default_state
        return super().write(vals)
