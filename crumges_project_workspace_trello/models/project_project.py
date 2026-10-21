# -*- coding: utf-8 -*-
from odoo import models, api

class ProjectProject(models.Model):
    _inherit = 'project.project'

    def write(self, vals):
        for project in self:
            # Bloquear cambio de workspace si ya está sincronizado a Trello
            if 'workspace_id' in vals and vals['workspace_id'] != project.workspace_id.id:
                if project.trello_sync and vals.get('trello_sync') is not False:
                    from odoo.exceptions import ValidationError
                    raise ValidationError(
                        "No puedes cambiar el Espacio de Trabajo de un proyecto que ya está sincronizado con Trello. "
                        "Por favor, deshabilita la sincronización con Trello primero si deseas moverlo de espacio."
                    )
            
            can_sync = 'trello_sync' in vals and vals.get('trello_sync')
            sync_requested = can_sync or 'trello_board_id' in vals
            
            # Si se está activando la sincronización y el proyecto tiene un workspace
            if sync_requested and (vals.get('trello_sync') or project.trello_sync) and project.workspace_id:
                workspace = project.workspace_id
                
                # Refrescar conteo real desde Trello antes de validar
                workspace.action_refresh_trello_boards()
                
                # Validar usando el límite real de Trello
                if workspace.trello_real_boards_count >= workspace.trello_max_boards:
                    # Crear nuevo workspace automáticamente clonando el nombre y agregando un sufijo numérico
                    import re
                    match = re.search(r'(\d+)$', workspace.name)
                    if match:
                        num = int(match.group(1)) + 1
                        base_name = workspace.name[:match.start()].strip()
                        new_name = f"{base_name} {num}"
                    else:
                        new_name = f"{workspace.name} 2"
                        
                    new_workspace = self.env['project.workspace'].create({
                        'name': new_name,
                        'company_id': workspace.company_id.id,
                        'description': workspace.description,
                        'trello_max_boards': workspace.trello_max_boards
                    })
                    # Sincronizar el nuevo workspace con Trello inmediatamente
                    new_workspace.action_sync_to_trello()
                    
                    # Reasignar este proyecto al nuevo workspace
                    vals['workspace_id'] = new_workspace.id
                    project.message_post(
                        body=f"<b>Aviso de Trello:</b> El espacio de trabajo anterior alcanzó su límite de tableros. Se ha creado y asignado automáticamente a <i>{new_name}</i>."
                    )

        # Inyectamos el ID de la organización de trello en el contexto para que res_users lo atrape
        # y lo mande a Trello al crear el tablero.
        projects_with_trello_ws = self.filtered(lambda p: p.workspace_id and p.workspace_id.trello_id)
        if projects_with_trello_ws:
            # Agrupamos por trello_id (asumiendo que en write usualmente pasamos de a un proyecto o a varios del mismo WS)
            # Para mayor robustez, tomamos el del primero. Si hay bulk writes en diferentes workspaces se inyectará el primero.
            trello_org_id = projects_with_trello_ws[0].workspace_id.trello_id
            self = self.with_context(trello_idOrganization=trello_org_id)
            
        return super(ProjectProject, self).write(vals)
