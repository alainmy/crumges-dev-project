.. contents:: 
   :local:

Approval Requirement for Projects
====================================
.. |badge1| image:: https://img.shields.io/badge/maturity-Beta-yellow.png

Este módulo permite enviar pruebas o muestras visuales (mockups, diseños, planos) a los clientes directamente desde una tarea de un proyecto para que sean aprobadas y firmadas digitalmente mediante un portal público.

Configuración
=============
Para configurar las etapas y textos por defecto:

1. Ve a **Proyectos > Configuración > Ajustes** (o en la vista del Proyecto específico).
2. Configura los textos por defecto para las pruebas (Nota al cliente y Declaración de conformidad).
3. Selecciona las etapas a las que se moverá la tarea automáticamente al enviar, aprobar y rechazar.

Modo de Uso
===========
1. Dentro de cualquier tarea, ve a la pestaña **Approval Requirements**.
2. Sube las imágenes de muestra e incluye una descripción (caption) para cada una.
3. Haz clic en **Send for Approval** para enviar un enlace tokenizado al cliente.
4. El cliente accederá al portal donde podrá visualizar las imágenes y **Aceptar (Firmar)** o **Rechazar** (con motivo).

**Por qué y Para qué:**
Esto evita el problema común de "Yo nunca aprobé eso" centralizando las aprobaciones en Odoo mediante actas formales PDF firmadas digitalmente por el cliente, en lugar de usar correos o WhatsApp.

**Regla de Extensión:**
Nativamente ese módulo no trae esta funcionalidad en Odoo Community. El módulo de Odoo Enterprise ``sign`` soluciona firmas de documentos, pero este módulo incluye un sistema de lienzo de firma en HTML5 totalmente gratuito y acoplado al pipeline del proyecto.

Caso de Uso
===========
Un estudio de diseño gráfico diseña un logo. En lugar de enviar un archivo por WhatsApp y recibir un "ok" informal, suben la imagen a la tarea y usan este módulo. El cliente recibe el enlace, lee los términos, dibuja su firma y el sistema genera automáticamente un acta PDF inmutable y mueve la tarea a "Aprobado".

Historial de Cambios
====================
- **18.0.1.0.0 (2026-06-26):** Versión inicial. Creación del módulo.

Reporte de Errores
==================
Por favor, reporta cualquier error en `GitHub Issues <https://github.com/Crumges/issues>`_.

Créditos
========
Autores
-------
* Crumges

Mantenedores
------------
* Crumges
