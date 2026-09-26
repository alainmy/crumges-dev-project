# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ProjectProject(models.Model):
    _inherit = 'project.project'

    def _resolve_project_by_trello_board(self, board_id, fallback=None):
        """Devuelve el proyecto exacto asociado a un board de Trello.

        Evita que dos proyectos distintos compartan el mismo board_id y que el sistema
        tome "el primer proyecto encontrado" al sincronizar tareas o webhooks.
        """
        projects = self.env['project.project'].sudo().search([('trello_board_reference', '=', board_id)])
        if fallback and fallback.trello_board_reference == board_id:
            return fallback
        if len(projects) == 1:
            return projects
        if fallback and fallback in projects:
            return fallback
        return self.env['project.project']

    trello_sync = fields.Boolean(
        string='Sincronizar con Trello',
        help="Si está activo, este proyecto se sincronizará con un tablero de Trello."
    )
                
    
    
    trello_board_id = fields.Many2one(
        'trello.board',
        string='Tablero de Trello',
        help="Selecciona un tablero existente o deja vacío para crear uno nuevo."
    )
    trello_board_reference = fields.Char(
        related='trello_board_id.trello_id',
        string='Trello Board Reference',
    )
    trello_board_url = fields.Char(
        related='trello_board_id.trello_url',
        string='URL del Tablero de Trello',
        help="Enlace directo al tablero en Trello.",
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

    def action_clear_trello_references(self):
        self.ensure_one()
        tasks = self.env['project.task'].sudo().search([('project_id', '=', self.id)])
        stages = self.env['project.task.type'].sudo().search([
            '|',
            ('project_ids', '=', self.id),
            ('id', 'in', tasks.mapped('stage_id').ids),
        ])
        tags = tasks.mapped('tag_ids').sudo()

        task_values = {}
        for field_name in ('trello_card_id',):
            if field_name in tasks._fields:
                task_values[field_name] = False
        if task_values:
            tasks.with_context(trello_cleanup=True).write(task_values)

        # Limpiar las relaciones project.trello.stage para este proyecto
        relations = self.env['project.trello.stage'].sudo().search([('project_id', '=', self.id)])
        relations.unlink()
        
        if 'trello_label_id' in tags._fields:
            tags.write({'trello_label_id': False})

        # Estos modelos pertenecen al módulo opcional de checklists.
        if 'checklist_ids' in tasks._fields:
            checklists = tasks.mapped('checklist_ids').sudo()
            if 'trello_checklist_id' in checklists._fields:
                checklists.write({'trello_checklist_id': False})
            if 'item_ids' in checklists._fields:
                items = checklists.mapped('item_ids').sudo()
                if 'trello_item_id' in items._fields:
                    items.write({'trello_item_id': False})

        # Al limpiar el board, los campos related de referencia y URL quedan vacíos.
        self.write({'trello_sync': False, 'trello_board_id': False})

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Referencias Trello limpiadas',
                'message': 'Se limpiaron las referencias Trello del proyecto, sus tareas, etapas, etiquetas y checklists.',
                'type': 'success',
                'sticky': False,
            },
        }

    def write(self, vals):
        res = super(ProjectProject, self).write(vals)
        for project in self:
            can_sync = 'trello_sync' in vals
            can_sync = can_sync and vals.get('trello_sync')
            if not can_sync:
                # Delete webhooks
                if project.trello_board_id and project.trello_board_id.webhook_id:
                    user = self.env['res.users']._get_trello_auth_user()
                    if user and user.trello_api_key and user.trello_token:
                        user._webhook_request('DELETE', f'/webhooks/{project.trello_board_id.webhook_id}')
                project.trello_board_id.unlink()
                continue
            sync_requested = can_sync or 'trello_board_id' in vals
            if sync_requested and project.trello_sync:
                if not project.trello_board_id:
                    user = self.env['res.users']._get_trello_auth_user()
                    if user and user.trello_api_key and user.trello_token:
                        # Buscar por nombre
                        board_info = user._trello_request('GET', '/members/me/boards', params={'fields': 'name,id,url'})
                        board_info = next((b for b in board_info if b.get('name') == project.name), None) if isinstance(board_info, list) else None
                        
                        # Buscar web hook
                        if board_info and isinstance(board_info, dict) and board_info.get('id'):
                            # Guardarlo en el caché de Odoo y vincularlo
                            
                            # Create a webhook
                            webhook_res = user._webhook_request('POST', '/webhooks', params={
                                'description': f'Webhook for board {board_info.get("name")}',
                                'callbackURL': self.env['ir.config_parameter'].sudo().get_param('web.base.url') + '/trello/webhook/update',
                                'idModel': board_info.get('id'),
                            })
                            if webhook_res and isinstance(webhook_res, dict) and webhook_res.get('id'):
                                webhook_url = webhook_res.get('callbackURL')
                                new_board = self.env['trello.board'].create({
                                    'name': board_info.get('name'),
                                    'trello_id': board_info.get('id'),
                                    'trello_url': board_info.get('url'),
                                    'webhook_url':webhook_url,
                                    'webhook_id': webhook_res.get('id'),
                                })
                                super(ProjectProject, project).write({
                                    'trello_board_id': new_board.id,
                                })
                                project.with_delay(channel='root.trello_sync')._initial_trello_sync(new_board.trello_id, is_new_board=True)
                                continue
                        # Crear el tablero en Trello
                        board_params = {'name': project.name}
                        trello_res = user._trello_request('POST', '/boards', params=board_params)
                        if trello_res and isinstance(trello_res, dict) and trello_res.get('id'):
                            # Guardarlo en el caché de Odoo y vincularlo
                            webhook_res = user._webhook_request('POST', '/webhooks', params={
                                                            'description': f'Webhook for board {trello_res.get("name")}',
                                                            'callbackURL': self.env['ir.config_parameter'].sudo().get_param('web.base.url') + '/trello/webhook/update',
                                                            'idModel': trello_res.get('id'),
                                                        })
                            if webhook_res and isinstance(webhook_res, dict) and webhook_res.get('id'):
                                webhook_url = webhook_res.get('callbackURL')
                                new_board = self.env['trello.board'].create({
                                    'name': trello_res.get('name'),
                                    'trello_id': trello_res.get('id'),
                                    'trello_url': trello_res.get('url'),
                                    'webhook_url': webhook_url,
                                    'webhook_id': webhook_res.get('id'),
                                })
                                # Usamos un super().write para evitar recursiones si tuviéramos lógica encadenada
                                super(ProjectProject, project).write({
                                    'trello_board_id': new_board.id,
                                })
                                # Iniciar sincronización masiva para el tablero nuevo
                                project.with_delay(channel='root.trello_sync')._initial_trello_sync(new_board.trello_id, is_new_board=True)
                        else:
                            super(ProjectProject, project).write({'trello_sync': False})
                            project.message_post(body="<p class='text-danger'><b>⚠️ Error de Trello:</b> Se ha alcanzado el límite de tableros. Elimina algunos y vuelve a encender el switch.</p>")
                elif project.trello_board_id and project.trello_board_reference:
                    # Si se vinculó un tablero existente, también sincronizamos
                    user = self.env['res.users']._get_trello_auth_user()
                    board_info = user._trello_request('GET', f'/boards/{project.trello_board_reference}') if user else False
                    url = board_info.get('url') if isinstance(board_info, dict) else False
                    if url:
                        project.trello_board_id.sudo().write({'trello_url': url})
                    project.with_delay(channel='root.trello_sync')._initial_trello_sync(project.trello_board_reference, is_new_board=False)

        return res

    def _initial_trello_sync(self, board_id, is_new_board=False):
        self.ensure_one()
        user = self.env['res.users']._get_trello_auth_user()
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
                    existing_relation = self.env['project.trello.stage'].search([
                        ('project_id', '=', self.id),
                        ('trello_list_id', '=', t_list.get('id')),
                    ], limit=1)
                    if not existing_relation:
                        existing_stage = self.env['project.task.type'].search([('name', '=', t_list.get('name'))], limit=1)
                        if not existing_stage:
                            existing_stage = self.env['project.task.type'].create({
                                'name': t_list.get('name'),
                                'project_ids': [(4, self.id)]
                            })
                        else:
                            existing_stage.project_ids = [(4, self.id)]
                        self.env['project.trello.stage'].set_trello_list_id(
                            self.id, existing_stage.id, t_list.get('id')
                        )

        # 3. Exportar Etapas (Columnas) de Odoo a Trello
        domain = ['|', ('project_ids', '=', self.id), ('id', 'in', self.task_ids.mapped('stage_id').ids)]
        stages = self.env['project.task.type'].search(domain)
        for stage in stages:
            existing_relation = self.env['project.trello.stage'].search([
                ('project_id', '=', self.id),
                ('stage_id', '=', stage.id),
            ], limit=1)
            if not existing_relation or not existing_relation.trello_list_id:
                res = user._trello_request('POST', '/lists', params={
                    'name': stage.name,
                    'idBoard': board_id,
                    'pos': 'bottom'
                })
                if res and isinstance(res, dict) and res.get('id'):
                    self.env['project.trello.stage'].set_trello_list_id(
                        self.id, stage.id, res['id']
                    )
                    
                    
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
                    relation = self.env['project.trello.stage'].search([
                        ('project_id', '=', self.id),
                        ('trello_list_id', '=', t_card.get('idList')),
                    ], limit=1)
                    stage = relation.stage_id if relation else False
                    
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
            user = self.env['res.users']._get_trello_auth_user()
            if user and user.trello_api_key and user.trello_token:
                domain = ['|', ('project_ids', '=', self.id), ('id', 'in', self.task_ids.mapped('stage_id').ids)]
                stages = self.env['project.task.type'].search(domain)
                for stage in stages:
                    relation = self.env['project.trello.stage'].search([
                        ('project_id', '=', self.id),
                        ('stage_id', '=', stage.id),
                    ], limit=1)
                    if not relation or not relation.trello_list_id:
                        res = user._trello_request('POST', '/lists', params={
                            'name': stage.name,
                            'idBoard': self.trello_board_reference,
                            'pos': 'bottom'
                        })
                        if res and isinstance(res, dict) and res.get('id'):
                            self.env['project.trello.stage'].set_trello_list_id(
                                self.id, stage.id, res['id']
                            )
                            
            self.with_delay(channel='root.trello_sync')._sync_trello_lists_order()
            return self._show_sync_notification('Sincronizando Etapas')

    def action_debug_sync_tasks_titles(self):
        self.ensure_one()
        user = self.env['res.users']._get_trello_auth_user()
        if not user or not user.trello_api_key or not user.trello_token: return
        for task in self.task_ids.filtered('trello_card_id'):
            user.with_delay(channel='root.trello_sync')._trello_request('PUT', f'/cards/{task.trello_card_id}', params={'name': task.name})
        return self._show_sync_notification('Sincronizando Títulos')

    def action_debug_sync_tags(self):
        self.ensure_one()
        user = self.env['res.users']._get_trello_auth_user()
        if not user or not user.trello_api_key or not user.trello_token: return
        for task in self.task_ids.filtered('trello_card_id'):
            task.with_delay(channel='root.trello_sync')._sync_to_trello('update') # Etiquetas
        return self._show_sync_notification('Sincronizando Etiquetas')

    def action_debug_sync_descriptions(self):
        self.ensure_one()
        user = self.env['res.users']._get_trello_auth_user()
        if not user or not user.trello_api_key or not user.trello_token: return
        from .trello_tools import html_to_trello_markdown
        for task in self.task_ids.filtered('trello_card_id'):
            desc = html_to_trello_markdown(task.description or '')
            user.with_delay(channel='root.trello_sync')._trello_request('PUT', f'/cards/{task.trello_card_id}', params={'desc': desc})
        return self._show_sync_notification('Sincronizando Descripciones')

    def action_trello_sync_now(self):
        self.ensure_one()
        if self.trello_sync and self.trello_board_reference:
            user = self.env['res.users']._get_trello_auth_user()
            if user and user.trello_api_key and user.trello_token:
                user.with_delay(channel='root.trello_sync')._trello_request('PUT', f'/boards/{self.trello_board_reference}', params={'name': self.name})
                
                # 2. Push stages (lists) if missing
                domain = ['|', ('project_ids', '=', self.id), ('id', 'in', self.task_ids.mapped('stage_id').ids)]
                stages = self.env['project.task.type'].search(domain)
                for stage in stages:
                    relation = self.env['project.trello.stage'].search([
                        ('project_id', '=', self.id),
                        ('stage_id', '=', stage.id),
                    ], limit=1)
                    if not relation or not relation.trello_list_id:
                        res = user._trello_request('POST', '/lists', params={
                            'name': stage.name,
                            'idBoard': self.trello_board_reference,
                            'pos': 'bottom'
                        })
                        if res and isinstance(res, dict) and res.get('id'):
                            self.env['project.trello.stage'].set_trello_list_id(
                                self.id, stage.id, res['id']
                            )
                            
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
        user = self.env['res.users']._get_trello_auth_user()
        if not user or not user.trello_api_key or not user.trello_token or not self.trello_board_reference:
            return
        domain = ['|', ('project_ids', '=', self.id), ('id', 'in', self.task_ids.mapped('stage_id').ids)]
        stages = self.env['project.task.type'].search(domain)
        for stage in stages:
            relation = self.env['project.trello.stage'].search([
                ('project_id', '=', self.id),
                ('stage_id', '=', stage.id),
            ], limit=1)
            if relation and relation.trello_list_id:
                user._trello_request('PUT', f'/lists/{relation.trello_list_id}', params={'pos': 'bottom'})
