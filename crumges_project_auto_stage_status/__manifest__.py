{
    'name': 'Automatización de Estado de Etapas en Proyectos',
    'version': '18.0.1.0.0',
    'category': 'Services/Project',
    'author': 'Crumges',
    'website': 'https://crumges.com',
    'summary': 'Configura un estado predeterminado para las etapas de tareas en Proyectos, automatizando el estado de la tarea.',
    'depends': [
        'project',
    ],
    'data': [
        'views/project_task_type_views.xml',
        'views/project_task_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'AGPL-3',
}
