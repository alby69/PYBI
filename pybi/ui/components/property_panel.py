"""Property panel component using a side drawer for node configuration."""

from typing import Callable, Dict, Any, Optional
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

    def __init__(self, on_save: Callable[[str, str, Dict[str, Any]], None], on_delete: Callable[[str], None]):
        self.on_save = on_save
        self.on_delete = on_delete
        self.drawer = ui.right_drawer(value=False).classes('bg-gray-50 border-l border-gray-200 p-4')
        self.drawer.style('width: 380px;')
        self.editing_node_id: Optional[str] = None
        self.current_kind: str = 'DataSource'
        self.field_inputs: Dict[str, Any] = {}

    def open_node(self, kind: str, node_id: Optional[str] = None, current_node: Optional[Dict[str, Any]] = None):
        """Open drawer to edit an existing node or build a new node."""
        self.editing_node_id = node_id
        self.current_kind = kind
        values = node_values(current_node) if current_node else default_values(kind)

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
                else:
                    inp = ui.input(field['label'], value=val)
                inp.classes('w-full mb-2')
                if field.get('help'):
                    inp.tooltip(field['help'])
                self.field_inputs[key] = inp

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
        return {key: (inp.value or '') for key, inp in self.field_inputs.items()}

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
