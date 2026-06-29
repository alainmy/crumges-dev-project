/** @odoo-module */

import { SubtaskKanbanList } from "@project/components/subtask_kanban_list/subtask_kanban_list";
import { patch } from "@web/core/utils/patch";

patch(SubtaskKanbanList.prototype, {
    /**
     * Override closedList to return ALL tasks instead of filtering out done/canceled tasks.
     * This provides better UX by letting users see the full list of subtasks right from the Kanban card.
     */
    get closedList() {
        // En Odoo 18, los widgets de las tarjetas Kanban (como este) están encapsulados.
        // No tienen acceso al contexto global de búsqueda de la vista (searchModel.domain).
        // Por lo tanto, para garantizar que el usuario pueda ver TODAS las subtareas al desplegar,
        // simplemente retornamos la lista completa de registros.
        return this.list.records.sort((subtask1, subtask2) => subtask1.resId - subtask2.resId);
    }
});
