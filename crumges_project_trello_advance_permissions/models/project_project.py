# -*- coding: utf-8 -*-
from odoo import models, fields

class ProjectProject(models.Model):
    _inherit = 'project.project'

    # Trello Permissions Matrix
    trello_allow_create_task = fields.Boolean(string="Permitir crear tareas desde Trello", default=True)
    trello_allow_move_task = fields.Boolean(string="Permitir mover tareas (Cambiar etapa) desde Trello", default=True)
    trello_allow_finish_task = fields.Boolean(string="Permitir finalizar tareas desde Trello", default=True)
    trello_allow_change_date = fields.Boolean(string="Permitir cambiar fecha de tareas desde Trello", default=True)
    trello_allow_check_checklist = fields.Boolean(string="Permitir tildar checklists desde Trello", default=True)
    trello_allow_archive_task = fields.Boolean(string="Permitir archivar tareas desde Trello", default=True)

    # Trello Tags Sync
    trello_allowed_tag_ids = fields.Many2many(
        'project.tags',
        relation='project_project_trello_tags_rel',
        column1='project_id',
        column2='tag_id',
        string="Etiquetas de Odoo permitidas en Trello",
        help="Solo estas etiquetas se sincronizarán y estarán disponibles en el tablero de Trello asociado."
    )

    # Trello Attachment Limits
    trello_allowed_file_type_ids = fields.Many2many(
        'trello.file.type',
        string="Tipos de archivo permitidos",
        help="Dejar vacío para permitir cualquier tipo de archivo que no supere el límite de tamaño."
    )
    trello_max_file_size = fields.Float(string="Tamaño máximo de archivo", default=5.0)
    trello_max_size_unit = fields.Selection([
        ('MB', 'Megabytes'),
        ('GB', 'Gigabytes')
    ], string="Unidad de tamaño", default='MB')
