"""Property panel component using a side drawer for node configuration."""

from typing import Callable, Dict, Any, List, Optional
from nicegui import ui

from pybi.etl.node_factory import (
    NODE_KINDS,
    build_node_data,
    default_values,
    fields_for,
    node_kind,
    node_values,
)


class PropertyPanel:
    """Side drawer panel for editing node parameters without blocking canvas modals."""

    def __init__(
        self,
        on_save: Callable[[str, str, Dict[str, Any]], None],
        on_delete: Callable[[str], None],
        file_options: Optional[Callable[[], List[str]]] = None,
    ):
        self.on_save = on_save
        self.on_delete = on_delete
        self.file_options = file_options
        self.drawer = ui.right_drawer(value=False).classes('bg-gray-50 border-l border-gray-200 p-4')
        self.drawer.style('width: 380px;')
        self.editing_node_id: Optional[str] = None
        self.current_kind: str = 'DataSource'
        self.field_inputs: Dict[str, Any] = {}
        self.applied_steps: List[Dict[str, Any]] = []

    def open_node(self, kind: str, node_id: Optional[str] = None, current_node: Optional[Dict[str, Any]] = None):
        """Open drawer to edit an existing node or build a new node."""
        self.editing_node_id = node_id
        self.current_kind = kind
        values = node_values(current_node) if current_node else default_values(kind)

        # Retrieve applied steps from node data if present
        data = (current_node.get('data') if current_node else {}) or {}
        self.applied_steps = list(data.get('applied_steps', []))

        self.drawer.clear()
        with self.drawer:
            title = f"Edit Node ({node_id})" if node_id else f"Add {NODE_KINDS[kind]['label']}"
            ui.label(title).classes('text-xl font-bold mb-4 text-gray-800')

            kind_select = ui.select(
                list(NODE_KINDS),
                label='Node Type',
                value=kind,
                on_change=lambda e: self.open_node(e.value, self.editing_node_id, current_node)
            ).classes('w-full mb-3')

            self.field_inputs.clear()
            for field in fields_for(kind):
                key = field['key']
                val = values.get(key, field.get('default', ''))
                if field['kind'] == 'choice':
                    inp = ui.select(field['options'], label=field['label'], value=val)
                elif field['kind'] == 'file' and self.file_options is not None:
                    options = list(self.file_options())
                    if val and val not in options:
                        options = [val] + options
                    inp = ui.select(
                        options,
                        label=field['label'],
                        value=val,
                        with_input=True,
                        new_value_mode='add-unique',
                    )
                else:
                    inp = ui.input(field['label'], value=val)
                inp.classes('w-full mb-2')
                if field.get('help'):
                    inp.tooltip(field['help'])
                self.field_inputs[key] = inp

            # Applied Steps sidebar section for Transform nodes
            if kind in ('Filter', 'Select', 'GroupBy', 'Pivot'):
                ui.separator().classes('my-3')
                ui.label('⚡ Applied Steps (Passaggi Applicati)').classes('text-sm font-bold text-gray-700 mb-1')
                steps_container = ui.column().classes('w-full gap-1 mb-2')

                def render_steps():
                    steps_container.clear()
                    with steps_container:
                        if not self.applied_steps:
                            ui.label('No applied steps defined.').classes('text-xs text-gray-400 italic')
                        else:
                            for idx, step in enumerate(self.applied_steps):
                                with ui.row().classes('w-full items-center justify-between bg-white border rounded p-1 text-xs'):
                                    ui.label(f"{idx+1}. {step.get('description', step.get('type', 'step'))}").classes('font-mono text-gray-700 flex-grow')
                                    with ui.row().classes('gap-1'):
                                        if idx > 0:
                                            ui.button(icon='arrow_upward', on_click=lambda i=idx: move_step(i, -1)).props('flat dense size=xs').tooltip('Move up')
                                        if idx < len(self.applied_steps) - 1:
                                            ui.button(icon='arrow_downward', on_click=lambda i=idx: move_step(i, 1)).props('flat dense size=xs').tooltip('Move down')
                                        ui.button(icon='close', on_click=lambda i=idx: remove_step(i)).props('flat dense size=xs color=negative').tooltip('Remove step')

                def move_step(idx, delta):
                    new_idx = idx + delta
                    if 0 <= new_idx < len(self.applied_steps):
                        self.applied_steps[idx], self.applied_steps[new_idx] = self.applied_steps[new_idx], self.applied_steps[idx]
                        render_steps()

                def remove_step(idx):
                    self.applied_steps.pop(idx)
                    render_steps()

                def add_step_dialog():
                    dialog = ui.dialog()
                    with dialog, ui.card().classes('w-80 p-4 gap-2'):
                        ui.label('Add Applied Step').classes('font-bold text-sm')
                        cond_inp = ui.input('Condition (e.g. region = \'EU\')', value="amount > 100").classes('w-full')
                        desc_inp = ui.input('Description', value="Filter amount > 100").classes('w-full')
                        def confirm_add():
                            if cond_inp.value:
                                self.applied_steps.append({
                                    'id': f'step_{len(self.applied_steps)+1}',
                                    'type': 'condition',
                                    'description': desc_inp.value or cond_inp.value,
                                    'config': {'condition': cond_inp.value}
                                })
                                dialog.close()
                                render_steps()
                        with ui.row().classes('w-full justify-end gap-2 mt-2'):
                            ui.button('Cancel', on_click=dialog.close).props('flat dense')
                            ui.button('Add Step', on_click=confirm_add).props('color=primary dense')
                    dialog.open()

                ui.button('+ Add Step', on_click=add_step_dialog).props('outline dense size=sm color=primary').classes('w-full mb-2')
                render_steps()

            with ui.row().classes('w-full justify-between items-center mt-6 gap-2'):
                if self.editing_node_id:
                    ui.button('Delete', on_click=self._handle_delete).props('color=negative outline dense')
                else:
                    ui.element('div')

                with ui.row().classes('gap-2'):
                    ui.button('Close', on_click=self.close).props('flat dense')
                    ui.button('Apply', on_click=self._handle_save).props('color=primary dense')

        self.drawer.set_value(True)

    def close(self):
        """Close the drawer."""
        self.drawer.set_value(False)

    def _collect_values(self) -> Dict[str, Any]:
        vals = {key: (inp.value or '') for key, inp in self.field_inputs.items()}
        if self.applied_steps:
            vals['applied_steps'] = self.applied_steps
        return vals

    def _handle_save(self):
        try:
            raw_vals = self._collect_values()
            build_node_data(self.current_kind, raw_vals)
            self.on_save(self.editing_node_id, self.current_kind, raw_vals)
            self.close()
        except ValueError as err:
            ui.notify(str(err), type='negative')

    def _handle_delete(self):
        if self.editing_node_id:
            self.on_delete(self.editing_node_id)
            self.close()
