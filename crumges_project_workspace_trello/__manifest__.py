# -*- coding: utf-8 -*-
{
    'name': 'Project Workspaces - Trello Integration',
    'version': '1.0',
    'category': 'Project Management',
    'summary': 'Sincroniza Espacios de Trabajo con Organizaciones de Trello',
    'description': """
        Este módulo actúa como puente entre crumges_project_workspace y crumges_trello_connector.
        Aplica los límites de tableros por espacio de trabajo de Trello (ej. 10 tableros).
        Si se alcanza el límite, crea automáticamente un nuevo espacio de trabajo.
    """,
    'author': 'Crumges',
    'website': 'https://www.crumges.com',
    'depends': ['crumges_project_workspace', 'crumges_trello_connector'],
    'data': [
        'views/project_workspace_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
