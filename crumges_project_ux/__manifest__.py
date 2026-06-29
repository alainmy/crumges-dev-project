{
    'name': 'Crumges Project UX',
    'version': '1.0',
    'summary': 'Mejoras de Experiencia de Usuario para Proyectos',
    'description': """
Crumges Project UX
==================
Este módulo incluye mejoras de usabilidad (UX) para el uso diario de la aplicación Proyectos:
* Al hacer clic en un proyecto desde la vista Kanban, redirige a la vista Formulario en lugar de las Tareas.
* Las subtareas dentro de las tarjetas Kanban ahora se desglosan por completo (incluyendo tareas cerradas).
    """,
    'category': 'Project',
    'author': 'Crumges',
    'website': 'https://crumges.com',
    'depends': ['project'],
    'data': [
        'views/project_project_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'crumges_project_ux/static/src/js/subtask_kanban_list_patch.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'OPL-1',
}
