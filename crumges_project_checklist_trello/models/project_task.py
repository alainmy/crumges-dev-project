# -*- coding: utf-8 -*-
from odoo import api, models, fields

class ProjectTask(models.Model):
    _inherit = 'project.task'

    checklist_ids = fields.One2many('project.task.checklist', 'task_id', string='Checklists')

    trello_checklist_summary = fields.Char(string="Progreso Checklists", compute="_compute_trello_checklist_summary", store=False)

    @api.depends('checklist_ids.item_ids.is_checked')
    def _compute_trello_checklist_summary(self):
        for task in self:
            items = task.checklist_ids.mapped('item_ids')
            total = len(items)
            if total > 0:
                checked = len(items.filtered(lambda i: i.is_checked))
                task.trello_checklist_summary = f"{checked}/{total}"
            else:
                task.trello_checklist_summary = ""

    def _normalize_identity_key(self, value):
        return (value or '').strip().lower()

    def _reconcile_checklist_duplicates_by_name(self):
        self.ensure_one()
        seen_checklists = {}
        for checklist in sorted(self.checklist_ids, key=lambda rec: (rec.sequence or 0, rec.id)):
            key = self._normalize_identity_key(checklist.identity_key or checklist.name)
            if not checklist.identity_key:
                checklist.with_context(trello_webhook_sync=True).write({'identity_key': key})

            existing = seen_checklists.get(key)
            if existing and existing.id != checklist.id:
                for item in sorted(checklist.item_ids, key=lambda rec: (rec.sequence or 0, rec.id)):
                    match = existing.item_ids.filtered(
                        lambda rec: self._normalize_identity_key(rec.identity_key or rec.name)
                        == self._normalize_identity_key(item.identity_key or item.name)
                    )
                    if match:
                        if item.trello_item_id and not match[0].trello_item_id:
                            match[0].with_context(trello_webhook_sync=True).write({'trello_item_id': item.trello_item_id})
                        item.with_context(trello_webhook_sync=True).unlink()
                    else:
                        item.with_context(trello_webhook_sync=True).write({'checklist_id': existing.id})
                checklist.with_context(trello_webhook_sync=True).unlink()
                continue

            seen_checklists[key] = checklist

        for checklist in self.checklist_ids:
            seen_items = {}
            for item in sorted(checklist.item_ids, key=lambda rec: (rec.sequence or 0, rec.id)):
                key = self._normalize_identity_key(item.identity_key or item.name)
                if not item.identity_key:
                    item.with_context(trello_webhook_sync=True).write({'identity_key': key})

                existing = seen_items.get(key)
                if existing and existing.id != item.id:
                    if item.trello_item_id and not existing.trello_item_id:
                        existing.with_context(trello_webhook_sync=True).write({'trello_item_id': item.trello_item_id})
                    item.with_context(trello_webhook_sync=True).unlink()
                    continue

                seen_items[key] = item

    def action_add_checklist(self):
        self.ensure_one()
        return {
            'name': 'Añadir Checklist',
            'type': 'ir.actions.act_window',
            'res_model': 'project.task.checklist.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_task_id': self.id}
        }

    def action_clean_duplicate_checklists(self):
        self.ensure_one()
        self._reconcile_checklist_duplicates_by_name()
        return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {'title': 'Duplicados limpiados', 'message': 'Los checklists e ítems duplicados fueron reconciliados por nombre.', 'type': 'success', 'sticky': False}}

    def _delete_trello_checklist(self, trello_checklist_id):
        user = self.env.user if self.env.user.trello_token else self.env['res.users'].sudo().search([('trello_token', '!=', False)], limit=1)
        if user and trello_checklist_id:
            user._trello_request('DELETE', f'/checklists/{trello_checklist_id}')

    def _delete_trello_checkitem(self, trello_checklist_id, trello_item_id):
        user = self.env.user if self.env.user.trello_token else self.env['res.users'].sudo().search([('trello_token', '!=', False)], limit=1)
        if user and trello_checklist_id and trello_item_id:
            user._trello_request('DELETE', f'/checklists/{trello_checklist_id}/checkItems/{trello_item_id}')

    def _sync_checklists_to_trello(self):
        self.ensure_one()
        self._reconcile_checklist_duplicates_by_name()
        if not self.trello_card_id:
            return

        user = self.env['res.users']._get_trello_auth_user()
        if not user or not user.trello_api_key or not user.trello_token:
            return

        for checklist in self.checklist_ids:
            current_trello_checklist_id = None
            current_key = self._normalize_identity_key(checklist.identity_key or checklist.name)
            if not checklist.identity_key:
                checklist.with_context(trello_webhook_sync=True).write({'identity_key': current_key})

            candidate = self.checklist_ids.filtered(lambda rec: rec.id != checklist.id and self._normalize_identity_key(rec.identity_key or rec.name) == current_key)
            if candidate and not checklist.trello_checklist_id and candidate[0].trello_checklist_id:
                checklist.with_context(trello_webhook_sync=True).write({'trello_checklist_id': candidate[0].trello_checklist_id})

            # Es un checklist
            if not checklist.trello_checklist_id:
                res = user._trello_request('POST', f'/cards/{self.trello_card_id}/checklists', params={'name': checklist.name})
                if res and res.get('id'):
                    checklist.with_context(trello_webhook_sync=True).write({'trello_checklist_id': res['id']})
                    current_trello_checklist_id = res['id']
            else:
                user._trello_request('PUT', f'/checklists/{checklist.trello_checklist_id}', params={'name': checklist.name})
                current_trello_checklist_id = checklist.trello_checklist_id

            # Sus ítems
            for item in checklist.item_ids:
                item_key = self._normalize_identity_key(item.identity_key or item.name)
                if not item.identity_key:
                    item.with_context(trello_webhook_sync=True).write({'identity_key': item_key})
                duplicate_item = checklist.item_ids.filtered(
                    lambda rec: rec.id != item.id and self._normalize_identity_key(rec.identity_key or rec.name) == item_key
                )
                if duplicate_item and not item.trello_item_id and duplicate_item[0].trello_item_id:
                    item.with_context(trello_webhook_sync=True).write({'trello_item_id': duplicate_item[0].trello_item_id})

                if not item.trello_item_id:
                    res = user._trello_request(
                        'POST',
                        f'/checklists/{current_trello_checklist_id}/checkItems',
                        params={'name': item.name, 'checked': 'true' if item.is_checked else 'false'}
                    )
                    if res and res.get('id'):
                        item.with_context(trello_webhook_sync=True).write({'trello_item_id': res['id']})
                else:
                    state = 'complete' if item.is_checked else 'incomplete'
                    user._trello_request(
                        'PUT',
                        f'/cards/{self.trello_card_id}/checklist/{current_trello_checklist_id}/checkItem/{item.trello_item_id}',
                        params={'name': item.name, 'state': state}
                    )