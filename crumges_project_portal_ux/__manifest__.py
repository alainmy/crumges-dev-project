{
    'name': 'Crumges Project Portal UX',
    'version': '1.0',
    'summary': 'Mejoras de Experiencia de Usuario para Proyectos en el Portal',
    'description': """
Crumges Project Portal UX
=========================
Este módulo incluye mejoras de usabilidad (UX) para los clientes en el portal web:
* Al acceder a un proyecto desde "Mis Proyectos", se mostrará la ficha técnica (información) del proyecto en lugar de la lista directa de tareas.
* Se incluye un botón para navegar a las tareas desde la ficha del proyecto.
    """,
    'category': 'Project',
    'author': 'Crumges',
    'website': 'https://crumges.com',
    'depends': ['project'],
    'data': [
        # 'security/ir.model.access.csv',
        'report/project_task_report.xml',
        'data/mail_template_data.xml',
        'views/portal_templates.xml',
        'views/project_task_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'crumges_project_portal_ux/static/src/scss/portal_tags.scss',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'OPL-1',
}
