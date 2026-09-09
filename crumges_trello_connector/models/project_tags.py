# -*- coding: utf-8 -*-
from odoo import models, fields

class ProjectTags(models.Model):
    _inherit = 'project.tags'

    trello_label_id = fields.Char(
        string='Trello Label ID',
        help="ID de la etiqueta de Trello vinculada a esta etiqueta de Odoo."
    )
