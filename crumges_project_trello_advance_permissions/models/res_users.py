# -*- coding: utf-8 -*-
from odoo import models, api, _
from markupsafe import Markup

class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def _process_trello_webhook_event(self, action_data):
        if action_data.get('appCreator'):
            return

        action_type = action_data.get('type')
        
        # Bloquear la importación de nuestros propios comentarios de restricción para evitar duplicados en el Chatter
        if action_type == 'commentCard':
            comment_text = action_data.get('data', {}).get('text', '')
            if "pero los permisos" in comment_text or "supera el límite" in comment_text or "no está permitido en este proyecto" in comment_text:
                return
                
        card_data = action_data.get('data', {}).get('card', {})
        board_id = action_data.get('data', {}).get('board', {}).get('id')
        member_name = action_data.get('memberCreator', {}).get('fullName', 'Desconocido')
        member_username = action_data.get('memberCreator', {}).get('username', '')
        
        user = self.env.user if self.env.user.trello_token else self.env['res.users'].sudo().search([('trello_token', '!=', False)], limit=1)
        if not user:
            return super()._process_trello_webhook_event(action_data)

        # Prevención de bucles infinitos:
        # Aseguramos que el ID del miembro de Odoo esté guardado para futuras referencias
        if user and not user.trello_member_id and user.trello_token:
            me_data = user._trello_request('GET', '/members/me')
            if isinstance(me_data, dict) and me_data.get('id'):
                user.sudo().write({'trello_member_id': me_data['id']})

        member_creator_id = action_data.get('memberCreator', {}).get('id')

        # Sincronizar o crear el usuario de Portal en Odoo
        if member_creator_id:
            odoo_user = self.env['res.users']._get_or_create_trello_user(member_creator_id, member_name)
        else:
            odoo_user = False
            
        trello_mention = f"@{member_username}" if member_username else member_name
        if odoo_user:
            odoo_mention = f'<a href="#" data-oe-model="res.partner" data-oe-id="{odoo_user.partner_id.id}">@{odoo_user.name}</a>'
        else:
            odoo_mention = member_name

        def _revert_and_notify(project, task, base_msg, revert_func=None):
            odoo_msg = base_msg.format(user=odoo_mention)
            trello_msg = base_msg.format(user=trello_mention)
            partner_ids = [odoo_user.partner_id.id] if odoo_user else []

            # 1. Post to Odoo Chatter
            if task:
                task.message_post(body=Markup(odoo_msg), partner_ids=partner_ids)
            elif project:
                project.message_post(body=Markup(odoo_msg), partner_ids=partner_ids)
                
            # 2. Revert in Trello (and add comment if applicable)
            if revert_func:
                revert_func()
            elif task:
                # Add Trello comment
                user.with_delay(channel='root.trello_sync')._trello_request('POST', f'/cards/{task.trello_card_id}/actions/comments', params={'text': trello_msg})
                # Force Odoo to push its truth back
                task.with_user(user).with_delay(channel='root.trello_sync')._sync_to_trello('update')
        
        # -------------------------------------------------------------
        # 1. CREATE CARD
        # -------------------------------------------------------------
        if action_type == 'createCard':
            if board_id:
                project = self.env['project.project'].sudo().search([('trello_board_reference', '=', board_id)], limit=1)
                if project and not project.trello_allow_create_task:
                    card_id = card_data.get('id')
                    if card_id:
                        # Si la tarea ya existe en Odoo con este ID, es porque Odoo la acaba de crear. No la borramos.
                        existing_task = self.env['project.task'].sudo().search([('trello_card_id', '=', card_id)], limit=1)
                        if existing_task:
                            pass
                        else:
                            base_msg = "El usuario {user} intentó crear una tarea desde Trello, pero los permisos del proyecto no lo permiten."
                            def revert_create(trello_msg):
                                user.with_delay(channel='root.trello_sync')._trello_request('DELETE', f'/cards/{card_id}')
                            _revert_and_notify(project, None, base_msg, revert_create)
                            return # Abort

        # -------------------------------------------------------------
        # For updates, we need the task
        # -------------------------------------------------------------
        card_id = card_data.get('id')
        if card_id:
            task = self.env['project.task'].sudo().search([('trello_card_id', '=', card_id)], limit=1)
            if task and task.project_id:
                project = task.project_id
                
                # 2. UPDATE CARD (Move, Rename, Desc, Archive, Due)
                if action_type == 'updateCard':
                    old_data = action_data.get('data', {}).get('old', {})
                    base_msg = None
                    
                    if 'idList' in old_data and not project.trello_allow_move_task:
                        if task.stage_id and task.stage_id.trello_list_id == card_data.get('idList'):
                            pass # Ignoramos porque Trello simplemente se está sincronizando con el estado actual de Odoo
                        else:
                            base_msg = "El usuario {user} intentó mover la tarea de etapa en Trello, pero los permisos no lo permiten."
                    elif 'name' in old_data:
                        if task.name != card_data.get('name'):
                            base_msg = "El usuario {user} intentó cambiar el título en Trello. Los nombres de las tareas solo se pueden modificar en Odoo."
                    elif 'desc' in old_data:
                        base_msg = "El usuario {user} intentó editar la descripción en Trello. El contenido y descripción solo se puede editar en Odoo."
                    elif 'dueComplete' in old_data and not project.trello_allow_finish_task:
                        is_completed = str(card_data.get('dueComplete', '')).lower() == 'true'
                        is_odoo_done = task.state == '1_done'
                        if is_completed != is_odoo_done:
                            base_msg = "El usuario {user} intentó finalizar/reabrir la tarea en Trello, pero los permisos del proyecto no lo permiten."
                    elif 'due' in old_data and not project.trello_allow_change_date:
                        base_msg = "El usuario {user} intentó cambiar la fecha límite en Trello, pero los permisos no lo permiten."
                    elif 'closed' in old_data and not project.trello_allow_archive_task:
                        is_closed_in_trello = str(card_data.get('closed', '')).lower() == 'true'
                        if is_closed_in_trello == (not task.active):
                            pass
                        else:
                            base_msg = "El usuario {user} intentó archivar/restaurar la tarea en Trello, pero los permisos no lo permiten."
                    
                    if base_msg:
                        _revert_and_notify(project, task, base_msg)
                        return # Abort

                # 3. TAGS
                # Odoo es mandatario absoluto de las etiquetas (creación y asignación)
                if action_type in ('addLabelToCard', 'removeLabelFromCard', 'createLabel'):
                    label_name = action_data.get('data', {}).get('label', {}).get('name', '')
                    if action_type == 'addLabelToCard':
                        odoo_tags = [t.name.lower() for t in task.tag_ids]
                        if label_name.lower() in odoo_tags:
                            pass # Ya la tiene Odoo
                        else:
                            base_msg = f"El usuario {{user}} intentó asignar una etiqueta en Trello ({label_name}). Las etiquetas se asignan exclusivamente desde Odoo."
                            _revert_and_notify(project, task, base_msg)
                            return
                    elif action_type == 'removeLabelFromCard':
                        base_msg = f"El usuario {{user}} intentó quitar una etiqueta en Trello. Las etiquetas se administran exclusivamente desde Odoo."
                        _revert_and_notify(project, task, base_msg)
                        return
                    elif action_type == 'createLabel':
                        base_msg = f"El usuario {{user}} intentó crear una nueva etiqueta en Trello ({label_name}). Odoo es el único sistema autorizado para crearlas."
                        _revert_and_notify(project, task, base_msg)
                        return

                # 4. CHECKLISTS
                # Odoo es el mandatario absoluto de la estructura. Bloqueamos incondicionalmente la creación desde Trello y avisamos al usuario.
                if action_type in ('addChecklistToCard', 'createCheckItem'):
                    base_msg = "El usuario {user} intentó agregar un checklist o ítem en Trello. La estructura del checklist debe ser administrada exclusivamente desde Odoo."
                    _revert_and_notify(project, task, base_msg)
                    # We also need to force sync the checklists back to revert the UI in Trello
                    if hasattr(task, '_sync_checklists_to_trello'):
                        task.with_user(user).with_delay(channel='root.trello_sync')._sync_checklists_to_trello()
                    return
                    
                if action_type == 'updateCheckItemStateOnCard' and not project.trello_allow_check_checklist:
                    base_msg = "El usuario {user} intentó marcar/desmarcar un checklist en Trello, pero los permisos no lo permiten."
                    _revert_and_notify(project, task, base_msg)
                    if hasattr(task, '_sync_checklists_to_trello'):
                        task.with_user(user).with_delay(channel='root.trello_sync')._sync_checklists_to_trello()
                    return

                # 5. ATTACHMENTS
                if action_type == 'addAttachmentToCard':
                    attachment = action_data.get('data', {}).get('attachment', {})
                    mime_type = attachment.get('contentType', '')
                    url = attachment.get('url', '')
                    name = attachment.get('name', '')
                    bytes_size = attachment.get('bytes', 0)
                    
                    # Size check
                    max_bytes = project.trello_max_file_size * (1024 * 1024) if project.trello_max_size_unit == 'MB' else project.trello_max_file_size * (1024 * 1024 * 1024)
                    if bytes_size and bytes_size > max_bytes:
                        base_msg = "Se ignoró el archivo '{name}' ({size:.2f} MB) desde Trello porque supera el límite de {max_size} {unit}.".format(
                            name=name, size=bytes_size / (1024*1024), max_size=project.trello_max_file_size, unit=project.trello_max_size_unit
                        )
                        def revert_attachment(trello_msg):
                            user.with_delay(channel='root.trello_sync')._trello_request('DELETE', f'/cards/{card_id}/attachments/{attachment.get("id")}')
                            task.message_post(body=trello_msg)
                        _revert_and_notify(project, None, base_msg, revert_attachment)
                        return
                        
                    # Extension/Mime check
                    allowed_types = project.trello_allowed_file_type_ids
                    if allowed_types:
                        allowed_mimes = allowed_types.mapped('mimetype')
                        if mime_type and mime_type not in allowed_mimes:
                            base_msg = f"Se ignoró el archivo '{name}' desde Trello porque su tipo ({mime_type}) no está permitido en este proyecto."
                            def revert_attachment2(trello_msg):
                                user.with_delay(channel='root.trello_sync')._trello_request('DELETE', f'/cards/{card_id}/attachments/{attachment.get("id")}')
                                task.message_post(body=trello_msg)
                            _revert_and_notify(project, None, base_msg, revert_attachment2)
                            return

        # If we reach here, it's allowed! Pass to original connector
        return super()._process_trello_webhook_event(action_data)
