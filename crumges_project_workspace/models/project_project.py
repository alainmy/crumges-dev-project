# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ProjectProject(models.Model):
    _inherit = 'project.project'

    def _default_workspace_id(self):
        workspace = self.env.ref('crumges_project_workspace.workspace_inbox', raise_if_not_found=False)
        return workspace.id if workspace else False

    workspace_id = fields.Many2one(
        'project.workspace', 
        string='Espacio de Trabajo',
        default=_default_workspace_id,
        domain="[('company_id', 'in', (False, company_id))]",
        help="Permite agrupar proyectos en espacios de trabajo."
    )

    @api.constrains('workspace_id', 'active')
    def _check_workspace_limit(self):
        for project in self:
            if project.workspace_id and project.workspace_id.max_projects > 0 and project.active:
                active_count = self.env['project.project'].search_count([
                    ('workspace_id', '=', project.workspace_id.id),
                    ('active', '=', True)
                ])
                if active_count > project.workspace_id.max_projects:
                    raise ValidationError(
                        f"El espacio de trabajo '{project.workspace_id.name}' ha alcanzado su límite máximo "
                        f"de {project.workspace_id.max_projects} proyectos activos.\n\n"
                        "No puedes crear ni desarchivar más proyectos aquí."
                    )
