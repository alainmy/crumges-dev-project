# -*- coding: utf-8 -*-
{
    'name': 'Project Workspaces',
    'version': '1.0',
    'category': 'Project Management',
    'summary': 'Introduce el concepto de Espacios de Trabajo para agrupar proyectos',
    'description': """
        Este módulo permite crear Espacios de Trabajo (Workspaces) para agrupar proyectos.
        Incluye un panel de búsqueda lateral (Search Panel) en la vista de proyectos para
        filtrar rápidamente por Workspace.
    """,
    'author': 'Crumges',
    'website': 'https://www.crumges.com',
    'depends': ['project'],
    'data': [
        'security/project_workspace_security.xml',
        'security/ir.model.access.csv',
        'data/project_workspace_type_data.xml',
        'data/project_workspace_data.xml',
        'views/project_workspace_type_views.xml',
        'views/project_workspace_views.xml',
        'views/project_project_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
