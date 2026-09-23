# -*- coding: utf-8 -*-
# Migración 18.0.1.1.0
# Divide el modelo antiguo 'project.task.checklist.line' (que mezclaba checklists
# con display_type='line_section' e ítems) en dos modelos:
#   - project.task.checklist
#   - project.task.checklist.item
# Conserva orden, estados e IDs de Trello.

import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

OLD_MODEL = 'project.task.checklist.line'


def migrate(cr, version):
    if not _table_exists(cr, 'project_task_checklist_line'):
        return

    env = api.Environment(cr, SUPERUSER_ID, {})
    checklist_env = env['project.task.checklist'].with_context(trello_webhook_sync=True)
    item_env = env['project.task.checklist.item'].with_context(trello_webhook_sync=True)

    cr.execute(
        """
        SELECT id, task_id, name, sequence, display_type, is_checked,
               trello_checklist_id, trello_item_id
        FROM project_task_checklist_line
        ORDER BY task_id, sequence, id
        """
    )
    rows = cr.dictfetchall()

    by_task = {}
    for row in rows:
        by_task.setdefault(row['task_id'], []).append(row)

    for task_id, task_rows in by_task.items():
        current_checklist = False
        orphans = []
        checklist_seq = 0
        item_seq = 0

        for row in task_rows:
            if row['display_type'] == 'line_section':
                checklist_seq += 1
                item_seq = 0
                current_checklist = checklist_env.create({
                    'task_id': task_id,
                    'name': row['name'] or 'Checklist',
                    'sequence': checklist_seq,
                    'trello_checklist_id': row['trello_checklist_id'],
                })
            else:
                item_seq += 1
                if current_checklist:
                    item_env.create({
                        'checklist_id': current_checklist.id,
                        'name': row['name'] or 'Ítem',
                        'sequence': item_seq,
                        'is_checked': bool(row['is_checked']),
                        'trello_item_id': row['trello_item_id'],
                    })
                else:
                    row['_seq'] = item_seq
                    orphans.append(row)

        if orphans:
            grouped = checklist_env.create({
                'task_id': task_id,
                'name': 'Elementos sueltos',
                'sequence': checklist_seq + 1,
            })
            for row in orphans:
                item_env.create({
                    'checklist_id': grouped.id,
                    'name': row['name'] or 'Ítem',
                    'sequence': row['_seq'],
                    'is_checked': bool(row['is_checked']),
                    'trello_item_id': row['trello_item_id'],
                })

    _drop_old_model(cr)


def _table_exists(cr, table_name):
    cr.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_name = %s",
        (table_name,),
    )
    return bool(cr.fetchone())


def _drop_old_model(cr):
    cr.execute("SELECT id FROM ir_model_fields WHERE model = %s", (OLD_MODEL,))
    field_ids = [r[0] for r in cr.fetchall()]
    if field_ids:
        cr.execute(
            "DELETE FROM ir_model_data WHERE model = 'ir.model.fields' AND res_id = ANY(%s::int[])",
            (field_ids,),
        )
        cr.execute(
            "DELETE FROM ir_model_fields WHERE id = ANY(%s::int[])",
            (field_ids,),
        )

    cr.execute("SELECT id FROM ir_model WHERE model = %s", (OLD_MODEL,))
    model_ids = [r[0] for r in cr.fetchall()]
    if not model_ids:
        _drop_legacy_table(cr)
        return

    cr.execute(
        "SELECT id FROM ir_model_access WHERE model_id = ANY(%s::int[])",
        (model_ids,),
    )
    access_ids = [r[0] for r in cr.fetchall()]
    if access_ids:
        cr.execute(
            "DELETE FROM ir_model_data WHERE model = 'ir.model.access' AND res_id = ANY(%s::int[])",
            (access_ids,),
        )
        cr.execute(
            "DELETE FROM ir_model_access WHERE id = ANY(%s::int[])",
            (access_ids,),
        )

    cr.execute(
        "DELETE FROM ir_model_data WHERE model = 'ir.model' AND res_id = ANY(%s::int[])",
        (model_ids,),
    )
    cr.execute(
        "DELETE FROM ir_model WHERE id = ANY(%s::int[])",
        (model_ids,),
    )

    _drop_legacy_table(cr)


def _drop_legacy_table(cr):
    cr.execute("DROP TABLE IF EXISTS project_task_checklist_line")
    _logger.info("Tabla obsoleta 'project_task_checklist_line' eliminada")