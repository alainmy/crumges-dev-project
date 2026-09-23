# -*- coding: utf-8 -*-
from odoo import api, fields, models

class ProjectTaskChecklistLine(models.Model):
    _name = 'project.task.checklist.line'
    _description = 'Task Checklist Line'
    _order = 'sequence, id'

    task_id = fields.Many2one('project.task', string='Task', required=True, ondelete='cascade', index=True)
    name = fields.Char(string='Name', required=True)
    sequence = fields.Integer(default=10)
    display_type = fields.Selection([
        ('line_section', 'Section'),
        ('line_note', 'Note')
    ], default=False, help="Technical field for UX purpose.")
    is_checked = fields.Boolean(string='Checked', default=False)
    
    trello_checklist_id = fields.Char(string='Trello Checklist ID', copy=False, index=True)
    trello_item_id = fields.Char(string='Trello Item ID', copy=False, index=True)

    section_progress = fields.Char(string="Progreso", compute="_compute_section_progress", store=False)

    @api.depends('is_checked', 'sequence', 'display_type', 'task_id.checklist_line_ids.is_checked', 'task_id.checklist_line_ids.sequence', 'task_id.checklist_line_ids.display_type')
    def _compute_section_progress(self):
        for line in self:
            if line.display_type == 'line_section':
                items = line._get_items()
                total = len(items)
                if total > 0:
                    checked = len(items.filtered(lambda i: i.is_checked))
                    line.section_progress = f"({checked}/{total})"
                else:
                    line.section_progress = "(0/0)"
            else:
                line.section_progress = ""

    def _get_items(self):
        self.ensure_one()
        if self.display_type != 'line_section':
            return self.env['project.task.checklist.line']
        items = self.env['project.task.checklist.line']
        lines = list(self.task_id.checklist_line_ids)
        if self in lines:
            my_index = lines.index(self)
            for item in lines[my_index+1:]:
                if item.display_type == 'line_section':
                    break
                if not item.display_type:
                    items += item
        return items

    def _get_parent_section(self):
        """Devuelve el ID de Trello de la sección a la que pertenece esta línea."""
        self.ensure_one()
        # Buscar la primera línea hacia arriba (menor secuencia o menor ID si igual secuencia) que sea sección
        sections = self.task_id.checklist_line_ids.filtered(lambda l: l.display_type == 'line_section')
        my_index = list(self.task_id.checklist_line_ids).index(self)
        for line in reversed(list(self.task_id.checklist_line_ids)[:my_index]):
            if line.display_type == 'line_section':
                return line
        return self.env['project.task.checklist.line']

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.task_id.trello_card_id and not self._context.get('trello_webhook_sync'):
                rec.task_id.with_delay(channel='root.trello_sync')._sync_checklists_to_trello()
        return records

    def write(self, vals):
        res = super().write(vals)
        if self._context.get('trello_webhook_sync'):
            return res
        if any(f in vals for f in ['name', 'sequence', 'is_checked']):
            for rec in self:
                if rec.task_id.trello_card_id:
                    rec.task_id.with_delay(channel='root.trello_sync')._sync_checklists_to_trello()
        return res

    def action_delete_line(self):
        self.ensure_one()
        self.unlink()

    def unlink(self):
        items_to_delete = self.env['project.task.checklist.line']
        for rec in self:
            if rec.display_type == 'line_section':
                items = rec._get_items()
                items_to_delete |= items

        for rec in self:
            if not self._context.get('trello_webhook_sync') and rec.task_id.trello_card_id:
                if rec.display_type == 'line_section' and rec.trello_checklist_id:
                    rec.task_id.with_delay(channel='root.trello_sync')._delete_trello_checklist(rec.trello_checklist_id)
                elif rec.trello_item_id:
                    parent = rec._get_parent_section()
                    if parent and parent.trello_checklist_id:
                        rec.task_id.with_delay(channel='root.trello_sync')._delete_trello_checkitem(parent.trello_checklist_id, rec.trello_item_id)
        
        res = super().unlink()
        if items_to_delete:
            items_to_delete.unlink()
        return res
