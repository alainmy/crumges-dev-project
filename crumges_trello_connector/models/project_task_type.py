# -*- coding: utf-8 -*-
from odoo import models, fields

class ProjectTaskType(models.Model):
    _inherit = 'project.task.type'

    trello_list_id = fields.Char(
        string='Trello List ID',
        help="ID de la lista de Trello vinculada a esta etapa."
    )
