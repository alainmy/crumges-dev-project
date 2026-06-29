from odoo import http, fields, _
from odoo.http import request
from odoo.exceptions import MissingError
import base64

class ProjectTaskApprovalRequirementPortal(http.Controller):

    @http.route(['/my/task/approval/<int:task_id>/<string:token>'], type='http', auth='public', website=True)
    def portal_approval_requirement_page(self, task_id, token, **kw):
        task = request.env['project.task'].sudo().browse(task_id)
        if not task.exists() or task.approval_token != token:
            raise MissingError(_("The requested proof does not exist or the token is invalid."))

        if task.project_id.approval_force_login and not request.session.uid:
            return request.redirect('/web/login?redirect=/my/task/approval/%s/%s' % (task_id, token))

        return request.render('crumges_project_task_approval_requirement.portal_approval_requirement_page', {
            'task': task,
            'token': token,
        })

    @http.route(['/my/task/approval/<int:task_id>/<string:token>/sign'], type='json', auth='public', website=True)
    def portal_approval_requirement_sign(self, task_id, token, name=None, signature=None, **kwargs):
        task = request.env['project.task'].sudo().browse(task_id)
        if not task.exists() or task.approval_token != token:
            return {'error': _('Invalid Token')}
            
        if signature and ',' in signature:
            signature = signature.split(',')[1]
            
        if task.approval_status in ['draft', 'sent']:
            task.write({
                'approval_status': 'approved',
                'approval_signed_by': name,
                'approval_signature': signature,
                'approval_signed_date': fields.Datetime.now()
            })
                
        return {
            'force_refresh': True,
            'redirect_url': '/my/tasks/%s?message=sign_ok' % task_id
        }

    @http.route(['/my/task/approval/<int:task_id>/<string:token>/reject'], type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def portal_approval_requirement_reject(self, task_id, token, **post):
        task = request.env['project.task'].sudo().browse(task_id)
        if not task.exists() or task.approval_token != token:
            raise MissingError(_("Invalid Token"))
            
        reason = post.get('reject_reason')
        if task.approval_status in ['draft', 'sent']:
            task.write({
                'approval_status': 'rejected',
                'approval_rejection_reason': reason
            })
                
        return request.redirect('/my/tasks/%s?message=reject_ok' % task_id)

    @http.route(['/my/task/approval/<int:task_id>/<string:token>/cancel'], type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def portal_approval_requirement_cancel(self, task_id, token, **post):
        task = request.env['project.task'].sudo().browse(task_id)
        if not task.exists() or task.approval_token != token:
            raise MissingError(_("Invalid Token"))
            
        reason = post.get('cancel_reason')
        if task.approval_status in ['draft', 'sent', 'rejected']:
            task.write({
                'approval_status': 'discontinued',
                'approval_rejection_reason': reason
            })
                
        return request.redirect('/my/tasks/%s?message=cancel_ok' % task_id)

    @http.route(['/my/task/approval/<int:task_id>/<string:token>/pdf'], type='http', auth='public')
    def portal_approval_requirement_pdf(self, task_id, token, **kw):
        task = request.env['project.task'].sudo().browse(task_id)
        if not task.exists() or task.approval_token != token or task.approval_status != 'approved':
            raise MissingError(_("Invalid Token or not approved yet"))
            
        pdf, _ = request.env['ir.actions.report'].sudo()._render_qweb_pdf('crumges_project_task_approval_requirement.action_report_approval_requirement', [task.id])
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf)),
            ('Content-Disposition', 'attachment; filename="Acta_Aprobacion_%s.pdf"' % task.id),
        ]
        return request.make_response(pdf, headers=pdfhttpheaders)
