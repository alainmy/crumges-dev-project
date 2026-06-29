from odoo import models

class Project(models.Model):
    _inherit = 'project.project'

    def _compute_access_url(self):
        super()._compute_access_url()
        for project in self:
            project.access_url = f'/my/projects/{project.id}/info'
