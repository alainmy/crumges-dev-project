# -*- coding: utf-8 -*-
from odoo import models, api

class ResUsers(models.Model):
    _inherit = 'res.users'

    def _trello_request(self, method, endpoint, params=None):
        # Interceptar creaciones de tableros para inyectar idOrganization si está en el contexto
        if method == 'POST' and endpoint == '/boards' and self.env.context.get('trello_idOrganization'):
            params = params or {}
            params['idOrganization'] = self.env.context.get('trello_idOrganization')
            
        return super(ResUsers, self)._trello_request(method, endpoint, params)
