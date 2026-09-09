# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ResUsers(models.Model):
    _inherit = 'res.users'

    trello_api_key = fields.Char(
        string='Trello API Key',
        help="Clave de API para conectar con Trello."
    )
    trello_token = fields.Char(
        string='Trello Token',
        help="Token de autorización para conectar con Trello."
    )

    trello_member_id = fields.Char(string='ID Trello', help="ID único del miembro en Trello", index=True)
    trello_sync_enabled = fields.Boolean(
        string='Sincronización Automática con Trello',
        help="Si está activo, sincronizará tareas con Trello en tiempo real.",
        default=False
    )

    def write(self, vals):
        res = super(ResUsers, self).write(vals)
        for user in self:
            if 'trello_sync_enabled' in vals:
                if vals['trello_sync_enabled']:
                    success = user._register_trello_webhook()
                    if success:
                        user._fetch_trello_boards()
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': 'Trello Sincronizado',
                                'message': 'Webhooks registrados y tableros descargados con éxito.',
                                'type': 'success',
                                'sticky': False,
                            }
                        }
                    else:
                        from odoo.exceptions import UserError
                        raise UserError("Error al conectar con Trello. Revisa tu API Key y Token.")
                else:
                    user._delete_trello_webhook()
        return res


    @api.model
    def _get_or_create_trello_user(self, member_id, fallback_name="Usuario Trello"):
        """Busca o crea un usuario de Portal para un miembro de Trello."""
        user = self.sudo().search([('trello_member_id', '=', member_id)], limit=1)
        if user:
            return user

        # Si no existe, buscamos info en Trello usando el token del usuario actual (si tiene)
        # o buscando algun usuario admin que tenga token
        trello_user = self.env.user if self.env.user.trello_token else self.sudo().search([('trello_token', '!=', False)], limit=1)
        
        name = fallback_name
        email = f"{member_id}@trello.local"
        avatar_url = False
        
        if trello_user and trello_user.trello_token:
            member_data = trello_user._trello_request('GET', f'/members/{member_id}')
            if isinstance(member_data, dict):
                name = member_data.get('fullName') or member_data.get('username') or fallback_name
                # Trello privacy might hide email
                if member_data.get('email'):
                    email = member_data['email']
                if member_data.get('avatarUrl'):
                    avatar_url = member_data['avatarUrl'] + "/170.png"

        # Buscar si ya hay partner/user con ese email
        existing_user = self.sudo().search([('login', '=', email)], limit=1)
        if existing_user:
            existing_user.trello_member_id = member_id
            return existing_user

        # Crear partner
        partner_vals = {
            'name': name,
            'email': email,
            'comment': 'Creado automáticamente desde Trello',
        }
        
        if avatar_url:
            import requests
            import base64
            try:
                resp = requests.get(avatar_url, timeout=5)
                if resp.status_code == 200:
                    partner_vals['image_1920'] = base64.b64encode(resp.content)
            except Exception:
                pass

        partner = self.env['res.partner'].sudo().create(partner_vals)
        
        # Publicar mensaje en chatter
        partner.message_post(body=f"Contacto creado por sincronización automática con Trello (Miembro ID: {member_id})")

        # Crear usuario de portal
        portal_group = self.env.ref('base.group_portal', raise_if_not_found=False)
        user_vals = {
            'name': name,
            'login': email,
            'partner_id': partner.id,
            'trello_member_id': member_id,
            'groups_id': [(6, 0, [portal_group.id])] if portal_group else [],
        }
        user = self.sudo().create(user_vals)
        return user

    def _fetch_trello_boards(self):
        self.ensure_one()
        boards = self._trello_request('GET', f'/tokens/{self.trello_token}/member/boards')
        if isinstance(boards, list):
            for board in boards:
                existing = self.env['trello.board'].search([('trello_id', '=', board.get('id'))], limit=1)
                if not existing:
                    self.env['trello.board'].create({
                        'name': board.get('name'),
                        'trello_id': board.get('id')
                    })

    def _trello_request(self, method, endpoint, params=None):
        self.ensure_one()
        import requests
        if not self.trello_api_key or not self.trello_token:
            return False
        
        url = f"https://api.trello.com/1{endpoint}"
        query = {
            'key': self.trello_api_key,
            'token': self.trello_token,
        }
        if params:
            query.update(params)
            
        try:
            response = requests.request(method, url, params=query, timeout=10)
            response.raise_for_status()
            return response.json() if response.content else True
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Trello API Error: {e}")
            return False

    def _register_trello_webhook(self):
        for user in self:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            callback_url = f"{base_url}/trello/webhook/update"
            
            # Obtener el ID del miembro asociado al token
            member_data = user._trello_request('GET', f'/tokens/{user.trello_token}/member')
            if not member_data or 'id' not in member_data:
                continue
            
            member_id = member_data['id']
            # Buscar webhooks existentes para no duplicar
            existing_webhooks = user._trello_request('GET', f'/tokens/{user.trello_token}/webhooks')
            webhook_id = False
            if isinstance(existing_webhooks, list):
                for wh in existing_webhooks:
                    if wh.get('callbackURL') == callback_url and wh.get('idModel') == member_id:
                        webhook_id = wh.get('id')
                        break
            
            if not webhook_id:
                # Crear nuevo webhook
                params = {
                    'callbackURL': callback_url,
                    'idModel': member_id,
                    'description': f'Odoo Sync Webhook for {user.name}'
                }
                res = user._trello_request('POST', '/webhooks', params=params)
                if not res:
                    return False
        return True

    def _delete_trello_webhook(self):
        for user in self:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            callback_url = f"{base_url}/trello/webhook/update"
            
            existing_webhooks = user._trello_request('GET', f'/tokens/{user.trello_token}/webhooks')
            if isinstance(existing_webhooks, list):
                for wh in existing_webhooks:
                    if wh.get('callbackURL') == callback_url:
                        user._trello_request('DELETE', f"/webhooks/{wh.get('id')}")

    @api.model
    def _process_trello_webhook_event(self, action_data):
        card_data = action_data.get('data', {}).get('card', {})
        action_type = action_data.get('type')

        trello_member_id = action_data.get('memberCreator', {}).get('id')
        user = self.env['res.users'].sudo().search([('trello_member_id', '=', trello_member_id)], limit=1)
        if not user or not user.trello_token:
            user = self.env['res.users'].sudo().search([('trello_token', '!=', False)], limit=1)


        # Eventos de Tablero
        if action_type == 'updateBoard':
            board_data = action_data.get('data', {}).get('board', {})
            board_id = board_data.get('id')
            if board_id and 'name' in board_data:
                project = self.env['project.project'].sudo().search([('trello_board_reference', '=', board_id)], limit=1)
                # Trello envia el nombre modificado. Si difiere de Odoo, forzamos revertirlo.
                if project and board_data.get('name') != project.name:

                    if user:
                        user.with_delay(channel='root.trello_sync')._trello_request('PUT', f'/boards/{board_id}', params={'name': project.name})
        
        if action_type == 'addMemberToBoard':
            member = action_data.get('member', {})
            board_id = action_data.get('data', {}).get('board', {}).get('id')
            if member.get('id') and board_id:
                project = self.env['project.project'].sudo().search([('trello_board_reference', '=', board_id)], limit=1)
                if project:
                    t_user = self._get_or_create_trello_user(member['id'], member.get('fullName'))
                    project.message_subscribe(partner_ids=[t_user.partner_id.id])
            return

        # Eventos de Listas (Etapas): Odoo Manda
        if action_type == 'updateList':
            list_data = action_data.get('data', {}).get('list', {})
            list_id = list_data.get('id')
            if list_id:
                stage = self.env['project.task.type'].sudo().search([('trello_list_id', '=', list_id)], limit=1)
                if stage:

                    if user:
                        params = {
                            'name': stage.name,
                            'closed': 'false'
                        }
                        user.with_delay(channel='root.trello_sync')._trello_request('PUT', f'/lists/{list_id}', params=params)
                        
                        # Si cambiaron la posición, restauramos el orden completo del tablero
                        if 'pos' in action_data.get('data', {}).get('old', {}):
                            board_id = action_data.get('data', {}).get('board', {}).get('id')
                            if board_id:
                                project = self.env['project.project'].sudo().search([('trello_board_reference', '=', board_id)], limit=1)
                                if project:
                                    project.with_delay(channel='root.trello_sync')._sync_trello_lists_order()
            return

        # Eventos de Miembros en Tarjeta
        if action_type == 'addMemberToCard':
            member = action_data.get('member', {})
            card_id = action_data.get('data', {}).get('card', {}).get('id')
            if member.get('id') and card_id:
                task_add = self.env['project.task'].sudo().search([('trello_card_id', '=', card_id)], limit=1)
                if task_add:
                    t_user = self._get_or_create_trello_user(member['id'], member.get('fullName'))
                    task_add.with_context(trello_webhook_sync=True).write({'user_ids': [(4, t_user.id)]})
                    task_add.message_subscribe(partner_ids=[t_user.partner_id.id])
            return
            
        if action_type == 'removeMemberFromCard':
            member = action_data.get('member', {})
            card_id = action_data.get('data', {}).get('card', {}).get('id')
            if member.get('id') and card_id:
                task_remove = self.env['project.task'].sudo().search([('trello_card_id', '=', card_id)], limit=1)
                if task_remove:
                    t_user = self.sudo().search([('trello_member_id', '=', member['id'])], limit=1)
                    if t_user:
                        task_remove.with_context(trello_webhook_sync=True).write({'user_ids': [(3, t_user.id)]})
                        task_remove.message_unsubscribe(partner_ids=[t_user.partner_id.id])
            return

        if not card_data.get('id'):
            return
            
        task = self.env['project.task'].sudo().search([('trello_card_id', '=', card_data['id'])], limit=1)
        
        # Si la tarea no existe en Odoo y la acción es crearla, la creamos.
        if not task:
            if action_type == 'createCard':
                list_id = action_data.get('data', {}).get('list', {}).get('id')
                board_id = action_data.get('data', {}).get('board', {}).get('id')
                if list_id and board_id:
                    stage = self.env['project.task.type'].sudo().search([('trello_list_id', '=', list_id)], limit=1)
                    project = self.env['project.project'].sudo().search([('trello_board_reference', '=', board_id)], limit=1)
                    if project:
                        self.env['project.task'].sudo().with_context(trello_webhook_sync=True).create({
                            'name': card_data.get('name', 'Nueva Tarea'),
                            'project_id': project.id,
                            'stage_id': stage.id if stage else False,
                            'trello_card_id': card_data['id'],
                        })
            return
            
        from .trello_tools import trello_markdown_to_html
        desc_html = trello_markdown_to_html(card_data.get('desc', ''))
            
        # Eventos de Etiquetas (auto-corrección forzada por Odoo)
        if action_type in ('addLabelToCard', 'removeLabelFromCard'):
            task.with_user(user).with_delay(channel='root.trello_sync')._sync_to_trello('update')
            return
            
        if 'name' in card_data or 'desc' in card_data or 'closed' in card_data or 'dueComplete' in card_data or 'due' in card_data or 'start' in card_data or 'idList' in card_data:
            vals = {}
            force_revert_to_trello = False
            
            # Bloquear Nombre y Descripción: Odoo manda.
            if 'name' in card_data and card_data['name'] != task.name:
                force_revert_to_trello = True
            
            if 'desc' in card_data:
                # Opcional: chequear si la descripción cambió, pero para evitar falsos positivos por formato Markdown vs HTML,
                # siempre forzamos re-sync si Trello reporta un cambio de descripción.
                force_revert_to_trello = True
                
            if 'closed' in card_data:
                vals['active'] = not card_data['closed']
            if 'dueComplete' in card_data:
                vals['state'] = '1_done' if card_data['dueComplete'] else '01_in_progress'
            if 'due' in card_data:
                vals['date_deadline'] = card_data['due'][:19].replace('T', ' ') if card_data['due'] else False
            if 'start' in card_data:
                vals['planned_date_begin'] = card_data['start'][:19].replace('T', ' ') if card_data['start'] else False
            if 'idList' in card_data and 'idList' in action_data.get('data', {}).get('old', {}):
                stage = self.env['project.task.type'].sudo().search([('trello_list_id', '=', card_data['idList'])], limit=1)
                if stage:
                    vals['stage_id'] = stage.id
                
            if vals:
                task.with_context(trello_webhook_sync=True).write(vals)
                
            if force_revert_to_trello:
                task.with_user(user).with_delay(channel='root.trello_sync')._sync_to_trello('update')
            
        # Comentarios
        if action_type == 'commentCard':
            member = action_data.get('memberCreator', {})
            text = action_data.get('data', {}).get('text', '')
            action_id = action_data.get('id', '')
            if text:
                import re
                from markupsafe import Markup
                
                # Mapear usuarios para las menciones (internos y de portal)
                users = self.env['res.users'].sudo().search([])
                user_map = {}
                for u in users:
                    norm_name = re.sub(r'[^a-zA-Z0-9]', '', u.name).lower()
                    user_map[norm_name] = u.partner_id.id
                    if u.login:
                        login_part = u.login.split('@')[0].lower()
                        user_map[login_part] = u.partner_id.id
                
                mentioned_partners = []
                def replace_mention(m):
                    username = m.group(1).lower()
                    partner_id = user_map.get(username)
                    if partner_id:
                        if partner_id not in mentioned_partners:
                            mentioned_partners.append(partner_id)
                        return f'<a href="#" data-oe-model="res.partner" data-oe-id="{partner_id}" class="o_mail_redirect">@{m.group(1)}</a>'
                    return m.group(0)
                
                # Transformar menciones
                text = re.sub(r'@([a-zA-Z0-9_]+)', replace_mention, text)
                
                # Trello markdown linebreaks
                text = text.replace('\n', '<br/>')
                
                body = Markup(f"<b>{member.get('fullName', 'Usuario de Trello')} comentó:</b><br/>{text}<!--{action_id}-->")
                
                # Evitar duplicados
                existing = self.env['mail.message'].sudo().search([('res_id', '=', task.id), ('model', '=', 'project.task'), ('body', 'ilike', action_id)], limit=1)
                if not existing:
                    task.with_context(trello_webhook_sync=True).message_post(body=body, partner_ids=mentioned_partners)
        # Adjuntos
        if action_type == 'addAttachmentToCard':
            attachment_data = action_data.get('data', {}).get('attachment', {})
            if attachment_data and attachment_data.get('url'):
                import requests
                import base64
                url = attachment_data['url']
                headers = {'Authorization': f'OAuth oauth_consumer_key="{user.trello_api_key}", oauth_token="{user.trello_token}"'}
                try:
                    resp = requests.get(url, headers=headers)
                    if resp.status_code == 200:
                        b64_data = base64.b64encode(resp.content)
                        att = self.env['ir.attachment'].sudo().create({
                            'name': attachment_data.get('name', 'adjunto_trello'),
                            'type': 'binary',
                            'datas': b64_data,
                            'res_model': 'project.task',
                            'res_id': task.id,
                        })
                        action_id = action_data.get('id', '')
                        from markupsafe import Markup
                        member = action_data.get('memberCreator', {})
                        task.with_context(trello_webhook_sync=True).message_post(
                            body=Markup(f"<b>{member.get('fullName', 'Usuario de Trello')} adjuntó:</b> {attachment_data.get('name', '')}<!--{action_id}-->"),
                            attachment_ids=[att.id]
                        )
                except Exception as e:
                    _logger.error("Error descargando adjunto de Trello: %s", e)    
        list_after = action_data.get('data', {}).get('listAfter', {})
        if list_after and list_after.get('id'):
            stage = self.env['project.task.type'].sudo().search([('trello_list_id', '=', list_after['id'])], limit=1)
            if stage:
                task.with_context(trello_webhook_sync=True).write({'stage_id': stage.id})

