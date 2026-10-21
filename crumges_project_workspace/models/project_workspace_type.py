# -*- coding: utf-8 -*-
from odoo import models, fields

class ProjectWorkspaceType(models.Model):
    _name = 'project.workspace.type'
    _description = 'Tipo de Espacio de Trabajo'
    _order = 'name'

    name = fields.Char(string='Nombre', required=True, translate=True)
