======================
Portal Backend Project
======================

.. |badge1| image:: https://img.shields.io/badge/maturity-Beta-yellow.png
.. |badge2| image:: https://img.shields.io/badge/license-AGPL--3-blue.png

.. contents::
   :local:

Configuración
=============
Para que este módulo tenga efecto, debes ir a *Ajustes > Usuarios* y seleccionar los permisos correspondientes de "Portal Proyecto" en la ficha de cada usuario híbrido. Existen dos niveles:
1. **Usuario (Solo Tareas Asignadas):** Puede ver todos los proyectos y editar/comentar únicamente en las tareas que se le han asignado explícitamente. No puede crear nuevas tareas.
2. **Administrador (Puede crear Tareas):** Hereda los permisos del nivel anterior, pero obtiene acceso de creación (Create) para generar nuevas tareas y subtareas en la base de datos.

Modo de Uso
===========
**Por qué y Para qué:**
Nativamente, los usuarios del portal solo tienen acceso limitado a sus proyectos desde la vista web del frontend. Este módulo permite elevar sus permisos para que puedan operar en el backend de Odoo con una interfaz profesional, facilitándoles la carga de adjuntos, partes de horas (timesheets) y la comunicación ágil con el equipo interno a través del Chatter de la vista de formulario nativa.

**Regla de Extensión:**
Este módulo es parte del stack de módulos de la familia ``portal_backend``. Extiende los permisos de acceso del módulo nativo ``project``.

Caso de Uso
===========
Un trabajador externo (freelancer o subcontratado) necesita registrar sus horas y cambiar el estado de las tareas Kanban directamente en la vista nativa de Odoo sin contar con una costosa licencia de "Usuario Interno". Gracias a este módulo, el administrador puede darle acceso restringido a la app de Proyectos, garantizando que el trabajador solo verá sus tareas asignadas y podrá reportar avances cómodamente.

Historial de Cambios
====================
- **18.0.1.0.0** (2026-07-01): Versión inicial. Implementación de reglas de acceso de lectura/escritura limitadas a las asignaciones del usuario y permisos de creación delegables.

Reporte de Errores
==================
Bugs are tracked on `GitHub Issues <https://github.com/Crumges/issues>`_. En caso de problemas, por favor revisa allí si el error ya ha sido reportado.

Créditos
========

Autores
-------
* Crumges

Mantenedores
------------
Este módulo es mantenido por Crumges.
