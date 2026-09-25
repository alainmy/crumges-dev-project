# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProjectTrelloStage(models.Model):
    _name = 'project.trello.stage'
    _description = 'Relación entre Etapa Odoo y Lista Trello por Proyecto'
    _unique_together = [('project_id', 'stage_id')]

    project_id = fields.Many2one(
        'project.project',
        string='Proyecto',
        required=True,
        ondelete='cascade',
        index=True,
    )
    stage_id = fields.Many2one(
        'project.task.type',
        string='Etapa Odoo',
        required=True,
        ondelete='cascade',
        index=True,
    )
    trello_list_id = fields.Char(
        string='ID de Lista Trello',
        help='ID único de la lista en Trello para este proyecto y etapa.',
        index=True,
    )

    def _get_or_create(self, project_id, stage_id):
        """Obtiene o crea la relación entre proyecto y etapa."""
        relation = self.search([
            ('project_id', '=', project_id),
            ('stage_id', '=', stage_id),
        ], limit=1)
        if not relation:
            relation = self.create({
                'project_id': project_id,
                'stage_id': stage_id,
            })
        return relation

    @api.model
    def get_trello_list_id(self, project_id, stage_id):
        """Devuelve el ID de lista Trello para proyecto + etapa."""
        relation = self.search([
            ('project_id', '=', project_id),
            ('stage_id', '=', stage_id),
        ], limit=1)
        return relation.trello_list_id if relation else False

    @api.model
    def set_trello_list_id(self, project_id, stage_id, trello_list_id):
        """Asigna el ID de lista Trello para proyecto + etapa."""
        relation = self._get_or_create(project_id, stage_id)
        relation.write({'trello_list_id': trello_list_id})
        return relation
