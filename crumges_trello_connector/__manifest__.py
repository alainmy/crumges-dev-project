# -*- coding: utf-8 -*-
{
    'name': 'Crumges Trello Connector',
    'version': '18.0.1.0.2',
    'category': 'Project Management',
    'author': 'Crumges',
    'website': 'https://crumges.com',
    'license': 'AGPL-3',
    'summary': 'Sincronización en tiempo real entre Odoo y Trello usando Webhooks y Queue Job.',
    'depends': [
        'base',
        'project',
        'queue_job',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/res_users_views.xml',
        'views/project_project_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
