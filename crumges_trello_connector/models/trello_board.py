# -*- coding: utf-8 -*-
from odoo import models, fields

class TrelloBoard(models.Model):
    _name = 'trello.board'
    _description = 'Trello Board Cache'

    name = fields.Char(string='Nombre del Tablero', required=True)
    trello_id = fields.Char(string='ID en Trello', required=True, index=True)
