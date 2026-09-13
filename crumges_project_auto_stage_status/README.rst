=================================================
Automatización de Estado de Etapas en Proyectos
=================================================

.. |badge1| image:: https://img.shields.io/badge/maturity-Beta-yellow.png
.. |badge2| image:: https://img.shields.io/badge/licence-AGPL--3-blue.png
.. |badge3| image:: https://img.shields.io/badge/github-Crumges-lightgray.png?logo=github

Configura un estado predeterminado para las etapas de tareas en Proyectos, automatizando el estado de la tarea.

.. contents::
   :local:

Configuración
=============

1. Vaya a Proyectos > Configuración > Etapas de Tarea.
2. Seleccione una etapa y defina el valor para "Default Status" (Estado por Defecto).
3. Podrá elegir entre todos los estados estándar configurados para las tareas.

Modo de Uso
===========

**Por qué y Para qué:**
En la gestión de proyectos ágil, mover una tarea a etapas lógicas (como "En Revisión" o "Completado") debería implicar un cambio automático en el estado de la tarea (el indicador visual de iconos) para evitar doble carga administrativa (mover la tarjeta y luego cambiar el estado). Este módulo resuelve esto automatizando el cambio.

**Regla de Extensión:**
Nativamente ese módulo no trae esta funcionalidad. Este módulo extiende el comportamiento base de `project.task` y `project.task.type` para inyectar este valor automáticamente al mover o crear el registro.

Caso de Uso
===========

Imaginemos un flujo de desarrollo:
- Etapa "To Do": Estado "En progreso".
- Etapa "Code Review": Estado "Cambios solicitados".
- Etapa "Done": Estado "Hecha".

Cuando el usuario arrastra la tarea desde "To Do" hacia "Done" en el tablero, el ícono de estado de la tarjeta cambiará automáticamente a un tick verde (Hecha).

Historial de Cambios
====================

* `18.0.1.0.0` (2026-08-10): Versión inicial.

Reporte de Errores
==================

Bugs are tracked on `GitHub Issues <https://github.com/Crumges/issues>`_.
In case of trouble, please check there if your issue has already been reported.

Créditos
========

Autores
-------

* Crumges

Mantenedores
------------

Este módulo es mantenido por Crumges.
