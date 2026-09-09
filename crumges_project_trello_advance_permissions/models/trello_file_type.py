# -*- coding: utf-8 -*-
from odoo import models, fields

class TrelloFileType(models.Model):
    _name = 'trello.file.type'
    _description = 'Trello Allowed File Type'

    name = fields.Char(string='Nombre (Ej: Imagen JPEG)', required=True)
    extension = fields.Char(string='Extensión (Ej: .jpg)', required=True)
    mimetype = fields.Char(string='MIME Type (Opcional)')
    active = fields.Boolean(default=True)
