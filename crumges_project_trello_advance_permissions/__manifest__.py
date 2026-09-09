# -*- coding: utf-8 -*-
{
    'name': 'Crumges Project Trello Advance Permissions',
    'version': '1.0',
    'category': 'Project Management',
    'summary': 'Advanced permissions, tag sync and attachment limits for Trello integration',
    'description': """
        Añade reglas granulares a la sincronización con Trello:
        - Matriz de permisos por proyecto (Crear tareas, Mover, Finalizar, etc).
        - Límites de tamaño y formato para archivos adjuntos.
        - Selección de etiquetas (Tags) a sincronizar por proyecto.
        - Sincronización de Archivados.
    """,
    'author': 'Crumges',
    'website': 'https://crumges.com',
    'depends': [
        'project',
        'crumges_trello_connector',
        'crumges_project_checklist_trello'
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/trello_file_type_data.xml',
        'views/trello_file_type_views.xml',
        'views/project_project_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'OPL-1',
}
