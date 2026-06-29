# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError, MissingError
from odoo.addons.project.controllers.portal import CustomerPortal

class ProjectPortalUX(CustomerPortal):

    @http.route(['/my/projects/<int:project_id>/info'], type='http', auth="public", website=True)
    def portal_my_project_info(self, project_id=None, access_token=None, **kw):
        try:
            project_sudo = self._document_check_access('project.project', project_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = {
            'project': project_sudo,
            'page_name': 'project_info',
        }
        
        return request.render("crumges_project_portal_ux.portal_project_info", values)

    def _prepare_tasks_values(self, page, date_begin, date_end, sortby, search, search_in, groupby, url="/my/tasks", domain=None, su=False, project=False):
        if not url.endswith('subtasks'):
            domain = (domain or []) + [('parent_id', '=', False)]
        return super()._prepare_tasks_values(page, date_begin, date_end, sortby, search, search_in, groupby, url=url, domain=domain, su=su, project=project)

    def _show_task_report(self, task_sudo, report_type, download):
        if report_type == 'pdf':
            return self._show_report(
                model=task_sudo, 
                report_type=report_type, 
                report_ref='crumges_project_portal_ux.action_report_project_task', 
                download=download
            )
        return super()._show_task_report(task_sudo, report_type, download)
