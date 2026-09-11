# -*- coding: utf-8 -*-
from odoo import models, fields

class ProjectProject(models.Model):
    _inherit = 'project.project'

    trello_sync = fields.Boolean(
        string='Sincronizar con Trello',
        help="Si está activo, este proyecto se sincronizará con un tablero de Trello."
    )
    trello_board_id = fields.Many2one(
        'trello.board',
        string='Tablero de Trello',
        help="Selecciona un tablero existente o deja vacío para crear uno nuevo."
    )
    trello_board_reference = fields.Char(string='Trello Board Reference')
    trello_board_url = fields.Char(
        string='URL del Tablero de Trello',
        help="Enlace directo al tablero en Trello."
    )
    
    stage_fold = fields.Boolean(related='stage_id.fold', string='Etapa Plegada')

    def action_archive_trello_board(self):
        self.ensure_one()
        if self.trello_board_reference:
            user = self.env.user if self.env.user.trello_token else self.sudo().search([('trello_token', '!=', False)], limit=1)
            if user:
                res = user._trello_request('PUT', f'/boards/{self.trello_board_reference}', params={'closed': 'true'})
                if res and res.get('closed'):
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': 'Tablero Archivado en Trello',
                            'message': 'El tablero ha sido archivado exitosamente para liberar cupo.',
                            'type': 'success',
                            'sticky': False,
                        }
                    }
        return True

    def write(self, vals):
        res = super(ProjectProject, self).write(vals)
        for project in self:
            if 'trello_sync' in vals and vals['trello_sync']:
                if not project.trello_board_id and not project.trello_board_reference:
                    user = self.env.user
                    if user.trello_api_key and user.trello_token:
                        # Crear el tablero en Trello
                        board_params = {'name': project.name}
                        trello_res = user._trello_request('POST', '/boards', params=board_params)
                        if trello_res and isinstance(trello_res, dict) and trello_res.get('id'):
                            # Guardarlo en el caché de Odoo y vincularlo
                            new_board = self.env['trello.board'].create({
                                'name': trello_res.get('name'),
                                'trello_id': trello_res.get('id')
                            })
                            # Usamos un super().write para evitar recursiones si tuviéramos lógica encadenada
                            super(ProjectProject, project).write({
                                'trello_board_id': new_board.id,
                                'trello_board_reference': new_board.trello_id,
                                'trello_board_url': trello_res.get('url')
                            })
                            # Iniciar sincronización masiva para el tablero nuevo
                            project.with_delay(channel='root.trello_sync')._initial_trello_sync(new_board.trello_id, is_new_board=True)
                        else:
                            super(ProjectProject, project).write({'trello_sync': False})
                            project.message_post(body="<p class='text-danger'><b>⚠️ Error de Trello:</b> Se ha alcanzado el límite de tableros. Elimina algunos y vuelve a encender el switch.</p>")
                elif project.trello_board_id and project.trello_board_reference:
                    # Si se vinculó un tablero existente, también sincronizamos
                    board_info = self.env.user._trello_request('GET', f'/boards/{project.trello_board_reference}')
                    url = board_info.get('url') if isinstance(board_info, dict) else False
                    if url:
                        super(ProjectProject, project).write({'trello_board_url': url})
                    project.with_delay(channel='root.trello_sync')._initial_trello_sync(project.trello_board_reference, is_new_board=False)

        return res

    def _initial_trello_sync(self, board_id, is_new_board=False):
        self.ensure_one()
        user = self.env.user
        if not user.trello_api_key or not user.trello_token:
            return

        # 1. Buscar y archivar listas por defecto de Trello (To Do, Doing, Done, etc.)
        lists = user._trello_request('GET', f'/boards/{board_id}/lists')
        if isinstance(lists, list):
            default_names = ['lista de tareas', 'en proceso', 'hecho', 'to do', 'doing', 'done']
            for lst in lists:
                if lst.get('name', '').lower() in default_names:
                    user._trello_request('PUT', f"/lists/{lst.get('id')}/closed", params={'value': 'true'})

        # 2. Importar Etapas de Trello a Odoo
        trello_lists = user._trello_request('GET', f'/boards/{board_id}/lists')
        if isinstance(trello_lists, list):
            for t_list in trello_lists:
                if t_list.get('name', '').lower() not in default_names:
                    existing_stage = self.env['project.task.type'].search([('trello_list_id', '=', t_list.get('id'))], limit=1)
                    if not existing_stage:
                        new_stage = self.env['project.task.type'].create({
                            'name': t_list.get('name'),
                            'trello_list_id': t_list.get('id'),
                            'project_ids': [(4, self.id)]
                        })

        # 3. Exportar Etapas (Columnas) de Odoo a Trello
        domain = ['|', ('project_ids', '=', self.id), ('id', 'in', self.task_ids.mapped('stage_id').ids)]
        stages = self.env['project.task.type'].search(domain)
        for stage in stages:
            if not stage.trello_list_id:
                res = user._trello_request('POST', '/lists', params={
                    'name': stage.name,
                    'idBoard': board_id,
                    'pos': 'bottom'
                })
                if res and isinstance(res, dict) and res.get('id'):
                    stage.write({'trello_list_id': res['id']})
                    
                    
        # 3.5 Importar Miembros del Tablero
        board_members = user._trello_request('GET', f'/boards/{self.trello_board_reference}/members')
        member_dict = {}
        if isinstance(board_members, list):
            for m in board_members:
                member_dict[m.get('id')] = m.get('fullName', 'Usuario de Trello')

        # 4. Importar Tarjetas de Trello a Odoo
        trello_cards = user._trello_request('GET', f'/boards/{self.trello_board_reference}/cards', params={'attachments': 'true'})
        if isinstance(trello_cards, list):
            import logging
            _logger = logging.getLogger(__name__)
            
            for t_card in trello_cards:
                existing_task = self.env['project.task'].search([('trello_card_id', '=', t_card.get('id'))], limit=1)
                task_to_sync = existing_task
                if not existing_task:
                    stage = self.env['project.task.type'].search([('trello_list_id', '=', t_card.get('idList'))], limit=1)
                    
                    from .trello_tools import trello_markdown_to_html
                    desc_html = trello_markdown_to_html(t_card.get('desc', ''))
                        
                    task_to_sync = self.env['project.task'].with_context(trello_webhook_sync=True).create({
                        'name': t_card.get('name', 'Nueva Tarea (Trello)'),
                        'description': desc_html,
                        'project_id': self.id,
                        'stage_id': stage.id if stage else False,
                        'trello_card_id': t_card.get('id'),
                        'state': '1_done' if t_card.get('dueComplete') else '01_in_progress',
                        'date_deadline': t_card.get('due')[:19].replace('T', ' ') if t_card.get('due') else False,
                        'planned_date_begin': t_card.get('start')[:19].replace('T', ' ') if t_card.get('start') else False
                    })
                    
                # Mapear asignados de la tarjeta
                idMembers = t_card.get('idMembers', [])
                if idMembers:
                    user_ids = []
                    for m_id in idMembers:
                        m_name = member_dict.get(m_id, 'Usuario de Trello')
                        t_user = self.env['res.users']._get_or_create_trello_user(m_id, m_name)
                        if t_user:
                            user_ids.append(t_user.id)
                    if user_ids:
                        task_to_sync.with_context(trello_webhook_sync=True).write({'user_ids': [(6, 0, user_ids)]})
                        partner_ids = self.env['res.users'].browse(user_ids).mapped('partner_id').ids
                        task_to_sync.message_subscribe(partner_ids=partner_ids)
                    
                # Importar adjuntos de la tarjeta (vital para tarjetas copiadas o ya existentes)
                attachments = t_card.get('attachments', [])
                for attachment_data in attachments:
                    if attachment_data.get('url'):
                        att_name = attachment_data.get('name', 'adjunto_trello')
                        existing_att = self.env['ir.attachment'].sudo().search([
                            ('res_model', '=', 'project.task'),
                            ('res_id', '=', task_to_sync.id),
                            ('name', '=', att_name)
                        ], limit=1)
                        if not existing_att:
                            import requests
                            import base64
                            url = attachment_data['url']
                            headers = {'Authorization': f'OAuth oauth_consumer_key="{user.trello_api_key}", oauth_token="{user.trello_token}"'}
                            try:
                                resp = requests.get(url, headers=headers)
                                if resp.status_code == 200:
                                    b64_data = base64.b64encode(resp.content)
                                    att = self.env['ir.attachment'].sudo().create({
                                        'name': att_name,
                                        'type': 'binary',
                                        'datas': b64_data,
                                        'res_model': 'project.task',
                                        'res_id': task_to_sync.id,
                                    })
                                    from markupsafe import Markup
                                    task_to_sync.with_context(trello_webhook_sync=True).message_post(
                                        body=Markup(f"<b>Adjunto de Trello:</b> {att_name}"),
                                        attachment_ids=[att.id]
                                    )
                            except Exception as e:
                                _logger.error("Error manual descargando adjunto de Trello: %s", e)

        # 5. Importar Historial (Comentarios y Adjuntos)
        trello_actions = user._trello_request('GET', f'/boards/{self.trello_board_reference}/actions', params={'filter': 'commentCard,addAttachmentToCard', 'limit': 1000})
        if isinstance(trello_actions, list):
            # Trello devuelve los más recientes primero, los invertimos para insertarlos en orden cronológico
            trello_actions.reverse()
            for action in trello_actions:
                card_data = action.get('data', {}).get('card', {})
                card_id = card_data.get('id')
                if not card_id:
                    continue
                    
                task = self.env['project.task'].search([('trello_card_id', '=', card_id)], limit=1)
                if not task:
                    continue
                    
                # Comprobar si ya existe el mensaje para evitar duplicados en la sincronización manual
                trello_action_id = action.get('id')
                existing_msg = self.env['mail.message'].search([('res_id', '=', task.id), ('model', '=', 'project.task'), ('body', 'ilike', trello_action_id)], limit=1)
                if existing_msg:
                    continue
                    
                member = action.get('memberCreator', {})
                if action.get('type') == 'commentCard':
                    text = action.get('data', {}).get('text', '')
                    if text:
                        # Usamos un comentario HTML invisible con el ID de la acción para evitar duplicados
                        from markupsafe import Markup
                        body = Markup(f"<b>{member.get('fullName', 'Usuario de Trello')} comentó:</b><br/>{text}<!--{trello_action_id}-->")
                        task.with_context(trello_webhook_sync=True).message_post(body=body)
                        
                elif action.get('type') == 'addAttachmentToCard':
                    attachment_data = action.get('data', {}).get('attachment', {})
                    if attachment_data and attachment_data.get('url'):
                        member = action.get('memberCreator', {})
                        att_name = attachment_data.get('name', 'adjunto_trello')
                        existing_att = self.env['ir.attachment'].sudo().search([
                            ('res_model', '=', 'project.task'),
                            ('res_id', '=', task.id),
                            ('name', '=', att_name)
                        ], limit=1)
                        
                        if not existing_att:
                            import requests
                            import base64
                            url = attachment_data['url']
                            headers = {'Authorization': f'OAuth oauth_consumer_key="{user.trello_api_key}", oauth_token="{user.trello_token}"'}
                            try:
                                resp = requests.get(url, headers=headers)
                                if resp.status_code == 200:
                                    b64_data = base64.b64encode(resp.content)
                                    att = self.env['ir.attachment'].sudo().create({
                                        'name': att_name,
                                        'type': 'binary',
                                        'datas': b64_data,
                                        'res_model': 'project.task',
                                        'res_id': task.id,
                                    })
                                    from markupsafe import Markup
                                    task.with_context(trello_webhook_sync=True).message_post(
                                        body=Markup(f"<b>{member.get('fullName', 'Usuario de Trello')} adjuntó:</b> {att_name}<!--{trello_action_id}-->"),
                                        attachment_ids=[att.id]
                                    )
                            except Exception as e:
                                _logger.error("Error manual descargando adjunto de Trello: %s", e)
                        else:
                            # Ya se descargó en el paso 4, solo publicamos el mensaje para el historial
                            from markupsafe import Markup
                            task.with_context(trello_webhook_sync=True).message_post(
                                body=Markup(f"<b>{member.get('fullName', 'Usuario de Trello')} adjuntó:</b> {att_name}<!--{trello_action_id}-->"),
                                attachment_ids=[existing_att.id]
                            )

        # 6. Exportar Tareas de Odoo a Trello
        for task in self.task_ids:
            if not task.trello_card_id:
                task._sync_to_trello('create')
            else:
                task._sync_to_trello('update')


    def _show_sync_notification(self, title):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': 'Se ha enviado la orden de sincronización (Debug).',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_debug_sync_stages(self):
        self.ensure_one()
        if self.trello_board_reference:
            user = self.env.user if self.env.user.trello_token else self.sudo().search([('trello_token', '!=', False)], limit=1)
            if user:
                domain = ['|', ('project_ids', '=', self.id), ('id', 'in', self.task_ids.mapped('stage_id').ids)]
                stages = self.env['project.task.type'].search(domain)
                for stage in stages:
                    if not stage.trello_list_id:
                        res = user._trello_request('POST', '/lists', params={
                            'name': stage.name,
                            'idBoard': self.trello_board_reference,
                            'pos': 'bottom'
                        })
                        if res and isinstance(res, dict) and res.get('id'):
                            stage.write({'trello_list_id': res['id']})
                            
            self.with_delay(channel='root.trello_sync')._sync_trello_lists_order()
            return self._show_sync_notification('Sincronizando Etapas')

    def action_debug_sync_tasks_titles(self):
        self.ensure_one()
        user = self.env.user
        if not user.trello_api_key or not user.trello_token: return
        for task in self.task_ids.filtered('trello_card_id'):
            user.with_delay(channel='root.trello_sync')._trello_request('PUT', f'/cards/{task.trello_card_id}', params={'name': task.name})
        return self._show_sync_notification('Sincronizando Títulos')

    def action_debug_sync_tags(self):
        self.ensure_one()
        user = self.env.user
        if not user.trello_api_key or not user.trello_token: return
        for task in self.task_ids.filtered('trello_card_id'):
            task.with_delay(channel='root.trello_sync')._sync_to_trello('update') # Etiquetas
        return self._show_sync_notification('Sincronizando Etiquetas')

    def action_debug_sync_descriptions(self):
        self.ensure_one()
        user = self.env.user
        if not user.trello_api_key or not user.trello_token: return
        from .trello_tools import html_to_trello_markdown
        for task in self.task_ids.filtered('trello_card_id'):
            desc = html_to_trello_markdown(task.description or '')
            user.with_delay(channel='root.trello_sync')._trello_request('PUT', f'/cards/{task.trello_card_id}', params={'desc': desc})
        return self._show_sync_notification('Sincronizando Descripciones')

    def action_trello_sync_now(self):
        self.ensure_one()
        if self.trello_sync and self.trello_board_reference:
            user = self.env.user if self.env.user.trello_token else self.sudo().search([('trello_token', '!=', False)], limit=1)
            if user:
                user.with_delay(channel='root.trello_sync')._trello_request('PUT', f'/boards/{self.trello_board_reference}', params={'name': self.name})
                
                # 2. Push stages (lists) if missing
                domain = ['|', ('project_ids', '=', self.id), ('id', 'in', self.task_ids.mapped('stage_id').ids)]
                stages = self.env['project.task.type'].search(domain)
                for stage in stages:
                    if not stage.trello_list_id:
                        res = user._trello_request('POST', '/lists', params={
                            'name': stage.name,
                            'idBoard': self.trello_board_reference,
                            'pos': 'bottom'
                        })
                        if res and isinstance(res, dict) and res.get('id'):
                            stage.write({'trello_list_id': res['id']})
                            
                self.with_delay(channel='root.trello_sync')._sync_trello_lists_order()
                
                # 3. Push all tasks unconditionally
                for task in self.task_ids:
                    if not task.trello_card_id:
                        task.with_delay(channel='root.trello_sync')._sync_to_trello('create')
                    else:
                        task.with_delay(channel='root.trello_sync')._sync_to_trello('update')
                        
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Sincronización Iniciada',
                    'message': 'Se ha enviado la orden de sobrescritura a Trello (Push Only).',
                    'type': 'success',
                    'sticky': False,
                }
            }

    def _sync_trello_lists_order(self):
        self.ensure_one()
        user = self.env.user if self.env.user.trello_token else self.env['res.users'].sudo().search([('trello_token', '!=', False)], limit=1)
        if not user or not self.trello_board_reference:
            return
        domain = ['|', ('project_ids', '=', self.id), ('id', 'in', self.task_ids.mapped('stage_id').ids)]
        stages = self.env['project.task.type'].search(domain)
        for stage in stages:
            if stage.trello_list_id:
                user._trello_request('PUT', f'/lists/{stage.trello_list_id}', params={'pos': 'bottom'})
