{
    "name": "Portal Backend Project",
    "summary": "Permite a los usuarios de Portal Backend acceder a Proyectos y gestionar sus Tareas",
    "version": "18.0.1.0.0",
    "category": "Project",
    "author": "Crumges",
    "website": "https://crumges.com",
    "license": "AGPL-3",
    "depends": [
        "portal_backend",
        "project",
        "portal_backend_mail"
    ],
    "data": [
        "security/res_groups.xml",
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        "views/base_menus.xml",
    ],
    "installable": True,
    "auto_install": False,
}
