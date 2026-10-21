# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ProjectWorkspace(models.Model):
    _name = 'project.workspace'
    _description = 'Espacio de Trabajo de Proyectos'
    _order = 'name'

    _sql_constraints = [
        ('check_max_projects_positive', 'CHECK(max_projects >= 0)', 'El límite de proyectos no puede ser negativo.')
    ]

    name = fields.Char(string='Nombre', required=True)
    type_id = fields.Many2one('project.workspace.type', string='Tipo de Espacio de trabajo')
    description = fields.Text(string='Descripción')
    max_projects = fields.Integer(string='Límite de Proyectos', default=0, required=True, help='0 significa sin límite. Evita que se creen o activen más proyectos si el espacio está lleno.')
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company)
    project_ids = fields.One2many('project.project', 'workspace_id', string='Proyectos')
    project_count = fields.Integer(string='Cantidad de Proyectos', compute='_compute_project_count')

    @api.depends('project_ids')
    def _compute_project_count(self):
        for record in self:
            record.project_count = len(record.project_ids)

    def action_view_projects(self):
        self.ensure_one()
        return {
            'name': 'Proyectos',
            'view_mode': 'kanban,list,form',
            'res_model': 'project.project',
            'domain': [('workspace_id', '=', self.id)],
            'type': 'ir.actions.act_window',
            'context': {'default_workspace_id': self.id}
        }
