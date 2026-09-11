# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ProjectTaskType(models.Model):
    _inherit = 'project.task.type'

    trello_list_id = fields.Char(
        string='Trello List ID',
        help="ID de la lista de Trello vinculada a esta etapa."
    )

    @api.model_create_multi
    def create(self, vals_list):
        stages = super(ProjectTaskType, self).create(vals_list)
        for stage in stages:
            if not stage.trello_list_id and stage.project_ids:
                # Si algún proyecto vinculado tiene trello_sync activo
                trello_project = stage.project_ids.filtered(lambda p: p.trello_sync and p.trello_board_reference)
                if trello_project:
                    stage.with_context(active_test=False).with_delay(channel='root.trello_sync')._sync_to_trello('create', trello_project[0])
        return stages

    def write(self, vals):
        res = super(ProjectTaskType, self).write(vals)
        if self._context.get('trello_webhook_sync'):
            return res
            
        if 'name' in vals:
            for stage in self.filtered('trello_list_id'):
                stage.with_context(active_test=False).with_delay(channel='root.trello_sync')._sync_to_trello('update')
        return res

    def _sync_to_trello(self, action, project=None):
        self.ensure_one()
        user = self.env.user if self.env.user.trello_token else self.env['res.users'].sudo().search([('trello_token', '!=', False)], limit=1)
        if not user or not user.trello_token:
            return
            
        if action == 'create' and project and project.trello_board_reference:
            res = user._trello_request('POST', '/lists', params={
                'name': self.name,
                'idBoard': project.trello_board_reference,
                'pos': 'bottom'
            })
            if res and isinstance(res, dict) and res.get('id'):
                self.sudo().write({'trello_list_id': res['id']})
                
        elif action == 'update' and self.trello_list_id:
            user._trello_request('PUT', f'/lists/{self.trello_list_id}', params={'name': self.name})
