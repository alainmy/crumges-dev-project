# -*- coding: utf-8 -*-
{
    'name': 'Crumges Project Checklist',
    'version': '18.0.1.0.0',
    'category': 'Project Management',
    'author': 'Crumges',
    'website': 'https://crumges.com',
    'license': 'AGPL-3',
    'summary': 'Añade Checklists multi-lista a las Tareas de Proyectos imitando la experiencia de Trello.',
    'depends': [
        'base',
        'project',
        'crumges_trello_connector',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/checklist_wizard_views.xml',
        'views/project_task_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
