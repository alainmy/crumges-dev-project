# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)

class TrelloWebhookController(http.Controller):

    @http.route('/trello/webhook/update', type='http', auth='public', methods=['POST', 'HEAD'], csrf=False)
    def trello_webhook(self, **post):
        # Trello sends a HEAD request when registering the webhook to verify the URL exists
        if request.httprequest.method == 'HEAD':
            return request.make_response('OK', headers=[('Content-Type', 'text/plain')])

        try:
            data = json.loads(request.httprequest.data.decode('utf-8'))
        except Exception as e:
            _logger.error("Error decoding Trello Webhook JSON: %s", e)
            return request.make_response('Bad Request', status=400)

        action = data.get('action', {})
        action_type = action.get('type')
        
        # Encolar el procesamiento para no bloquear la respuesta rápida a Trello
        # Se requiere auth='public', por lo que usamos sudo() para encolar
        env = request.env(su=True)
        env['res.users'].with_delay(channel='root.trello_sync')._process_trello_webhook_event(action)

        return request.make_response('OK', headers=[('Content-Type', 'text/plain')])
