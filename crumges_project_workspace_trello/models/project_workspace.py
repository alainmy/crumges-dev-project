# -*- coding: utf-8 -*-
from odoo import models, fields, api
import re

class ProjectWorkspace(models.Model):
    _inherit = 'project.workspace'

    trello_id = fields.Char(string='Trello Organization ID', readonly=True)
    trello_url = fields.Char(string='URL Trello', readonly=True)
    trello_max_boards = fields.Integer(string='Límite de Tableros Trello', default=10, required=True)
    trello_active_boards_count = fields.Integer(
        string='Tableros Trello Activos', 
        compute='_compute_trello_active_boards_count'
    )
    trello_real_boards_count = fields.Integer(string='Tableros Reales en Trello', readonly=True)

    @api.depends('project_ids', 'project_ids.trello_sync', 'project_ids.trello_board_reference')
    def _compute_trello_active_boards_count(self):
        for record in self:
            # Contamos proyectos activos que están sincronizados a Trello
            active_projects = record.project_ids.filtered(lambda p: p.trello_sync and p.trello_board_reference)
            record.trello_active_boards_count = len(active_projects)

    def action_sync_to_trello(self):
        self.ensure_one()
        user = self.env['res.users']._get_trello_auth_user()
        if not user or not user.trello_api_key or not user.trello_token:
            from odoo.exceptions import UserError
            raise UserError("No hay credenciales válidas de Trello configuradas en el sistema.")

        if not self.trello_id:
            # Crear la organización (Workspace) en Trello
            params = {
                'displayName': self.name,
                'name': re.sub(r'[^a-zA-Z0-9]', '', self.name).lower() + str(self.id) # Debe ser alfanumérico y único
            }
            if self.description:
                params['desc'] = self.description
                
            res = user._trello_request('POST', '/organizations', params=params)
            if res and isinstance(res, dict) and res.get('id'):
                self.write({
                    'trello_id': res.get('id'),
                    'trello_url': res.get('url')
                })
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Sincronizado',
                        'message': 'Espacio de trabajo creado en Trello exitosamente.',
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                from odoo.exceptions import UserError
                raise UserError("Hubo un error al intentar crear el espacio de trabajo en Trello.")
        return True

    def action_refresh_trello_boards(self):
        for record in self:
            if record.trello_id:
                user = self.env['res.users']._get_trello_auth_user()
                if user and user.trello_api_key and user.trello_token:
                    res = user._trello_request('GET', f'/organizations/{record.trello_id}/boards')
                    if isinstance(res, list):
                        record.trello_real_boards_count = len(res)
        return True
