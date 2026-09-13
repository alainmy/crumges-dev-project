from odoo import models, fields

class ProjectTask(models.Model):
    _inherit = 'project.task'

    @property
    def SELF_READABLE_FIELDS(self):
        fields = super().SELF_READABLE_FIELDS
        if self.env.user.has_group('portal_backend_project.group_portal_backend_project_user'):
            return fields | set(self._fields.keys())
        return fields

    @property
    def SELF_WRITABLE_FIELDS(self):
        fields = super().SELF_WRITABLE_FIELDS
        if self.env.user.has_group('portal_backend_project.group_portal_backend_project_user'):
            return fields | set(self._fields.keys())
        return fields

    user_ids = fields.Many2many(
        domain=lambda self: [
            '|',
            ('share', '=', False),
            ('groups_id', 'in', self.env.ref('portal_backend_project.group_portal_backend_project_user').id)
        ]
    )
