# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ProjectTask(models.Model):
    _inherit = 'project.task'

    trello_card_id = fields.Char(
        string='Trello Card ID',
        help="ID de la tarjeta de Trello vinculada a esta tarea."
    )
    

    user_ids = fields.Many2many(
        'res.users', relation='project_task_user_rel', column1='task_id', column2='user_id',
        domain="[('active', '=', True)]",
        string='Assignees'
    )

    @api.model_create_multi
    def create(self, vals_list):
        tasks = super(ProjectTask, self).create(vals_list)
        for task in tasks:
            if not task.trello_card_id and task.project_id.trello_board_id:
                task.with_context(active_test=False).with_delay(channel='root.trello_sync')._sync_to_trello('create')
        return tasks

    def write(self, vals):
        res = super(ProjectTask, self).write(vals)
        if self._context.get('trello_webhook_sync'):
            return res
            
        fields_to_sync = [
            'name', 'description', 'project_id', 'stage_id', 'date_deadline',
            'planned_date_begin', 'active', 'state', 'tag_ids', 'user_ids',
        ]
        if any(f in vals for f in fields_to_sync):
            for task in self:
                if task.project_id.trello_board_id:
                    task.with_context(active_test=False).with_delay(channel='root.trello_sync')._sync_to_trello('update')
        return res

    def _sync_to_trello(self, action):
        self.ensure_one()
        user = self.env['res.users']._get_trello_auth_user()
        if not user.trello_api_key or not user.trello_token:
            return
            
        from .trello_tools import html_to_trello_markdown
        desc = html_to_trello_markdown(self.description or '')
        
        params = {
            'name': self.name,
            'desc': desc,
            'closed': 'false' if self.active else 'true',
        }
        
        if hasattr(self, 'tag_ids') and self.project_id.trello_board_reference:
            board_id = self.project_id.trello_board_reference
            board_labels = user._trello_request('GET', f'/boards/{board_id}/labels') or []
            label_map = {l.get('name', '').lower(): l.get('id') for l in board_labels if l.get('name')}
            id_labels = []
            
            # Mapeo oficial de Odoo a Trello
            color_map = {
                1: 'red', 2: 'orange', 3: 'yellow', 4: 'sky', 
                5: 'purple', 6: 'pink', 7: 'sky', 8: 'blue', 
                9: 'red', 10: 'green', 11: 'purple'
            }
            
            for tag in self.tag_ids:
                tag_name = tag.name.lower()
                if tag_name in label_map:
                    id_labels.append(label_map[tag_name])
                else:
                    color = color_map.get(tag.color, 'null')
                    params_label = {'name': tag.name, 'idBoard': board_id}
                    if color != 'null':
                        params_label['color'] = color
                    else:
                        params_label['color'] = 'null'
                        
                    new_label = user._trello_request('POST', f'/labels', params=params_label)
                    if new_label and isinstance(new_label, dict) and new_label.get('id'):
                        id_labels.append(new_label.get('id'))
                        label_map[tag_name] = new_label.get('id')
            params['idLabels'] = ','.join(id_labels)
        
        if self.date_deadline:
            params['due'] = self.date_deadline.isoformat()
        else:
            params['due'] = 'null'
            
        if hasattr(self, 'planned_date_begin') and self.planned_date_begin:
            params['start'] = self.planned_date_begin.isoformat()
        else:
            params['start'] = 'null'
            
        if hasattr(self, 'state'):
            params['dueComplete'] = 'true' if self.state == '1_done' else 'false'
        if self.stage_id and self.project_id:
            trello_list_id = self.env['project.trello.stage'].get_trello_list_id(
                self.project_id.id, self.stage_id.id
            )
            if trello_list_id:
                params['idList'] = trello_list_id
            
        if action == 'create':
            params['idBoard'] = self.project_id.trello_board_reference
            if not params.get('idList'):
                try:
                    from odoo.addons.queue_job.exception import RetryableJobError
                    raise RetryableJobError("El ID de la lista de Trello aún no está disponible para esta etapa. Reintentando...")
                except ImportError:
                    return
            res = user._trello_request('POST', '/cards', params=params)
            if res and isinstance(res, dict) and res.get('id'):
                super(ProjectTask, self).write({'trello_card_id': res['id']})
        elif action == 'update' and self.trello_card_id:
            user._trello_request('PUT', f'/cards/{self.trello_card_id}', params=params)

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        message = super(ProjectTask, self).message_post(**kwargs)
        
        if self.env.context.get('trello_webhook_sync') or not self.trello_card_id:
            return message
            
        msg_type = kwargs.get('message_type', message.message_type)
        if msg_type != 'comment':
            return message
            
        body_html = kwargs.get('body', message.body)
        if not body_html:
            return message
            
        from .trello_tools import html_to_trello_markdown
        text = html_to_trello_markdown(body_html)
        
        user = self.env['res.users']._get_trello_auth_user()
        if user.trello_api_key and user.trello_token:
            res = user._trello_request('POST', f'/cards/{self.trello_card_id}/actions/comments', params={'text': text})
            if res and isinstance(res, dict) and res.get('id'):
                message.sudo().write({'body': f"{message.body}<!--{res['id']}-->"})
                
        return message
