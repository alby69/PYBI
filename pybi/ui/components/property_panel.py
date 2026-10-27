"""Property panel component using a side drawer for node configuration."""

from typing import Callable, Dict, Any, List, Optional, Tuple
from nicegui import ui

from pybi.etl.calculated import apply_calculated_column, build_calculated_expression
from pybi.etl.column_inspector import as_list
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
        source_columns_provider: Optional[Callable[[Dict[str, Any]], List[str]]] = None,
        join_columns_provider: Optional[Callable[[str], List[Tuple[str, List[str]]]]] = None,
        upstream_columns_provider: Optional[Callable[[str], List[str]]] = None,
        sample_frame_provider: Optional[Callable[[str], Any]] = None,
    ):
        self.on_save = on_save
        self.on_delete = on_delete
        self.file_options = file_options
        self.source_columns_provider = source_columns_provider
        self.join_columns_provider = join_columns_provider
        self.upstream_columns_provider = upstream_columns_provider
        self.sample_frame_provider = sample_frame_provider
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

            # Resolve the real column names of the two Join inputs (if wired).
            join_sides: List[Tuple[str, List[str]]] = []
            if kind == 'Join' and self.join_columns_provider is not None and node_id:
                join_sides = list(self.join_columns_provider(node_id))
            join_left: List[str] = join_sides[0][1] if join_sides else []
            join_right: List[str] = join_sides[1][1] if len(join_sides) > 1 else []

            upstream_columns: List[str] = []
            if kind == 'AddColumn' and node_id and self.upstream_columns_provider is not None:
                upstream_columns = list(self.upstream_columns_provider(node_id))

            self.field_inputs.clear()
            for field in fields_for(kind):
                key = field['key']
                val = values.get(key, field.get('default', ''))
                column_options: Optional[List[str]] = None
                if kind == 'Join' and node_id:
                    if key == 'left_on':
                        column_options = join_left
                    elif key == 'right_on':
                        column_options = join_right
                if column_options:
                    current = as_list(val)
                    options = list(column_options)
                    for column in current:
                        if column not in options:
                            options.append(column)
                    inp = ui.select(
                        options,
                        label=field['label'],
                        value=current,
                        multiple=True,
                        with_input=True,
                        new_value_mode='add-unique',
                    )
                elif field['kind'] == 'columns':
                    current = as_list(val)
                    if upstream_columns:
                        options = list(upstream_columns)
                        for column in current:
                            if column not in options:
                                options.append(column)
                        inp = ui.select(
                            options,
                            label=field['label'],
                            value=current,
                            multiple=True,
                            with_input=True,
                            new_value_mode='add-unique',
                        )
                    else:
                        inp = ui.input(field['label'], value=", ".join(current))
                elif field['kind'] == 'bool':
                    trim = val
                    if isinstance(trim, str):
                        trim = trim.strip().lower() not in ('false', '0', 'no', 'off', '')
                    inp = ui.checkbox(field['label'], value=bool(trim))
                elif field['kind'] == 'choice':
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

            if kind == 'DataSource' and self.source_columns_provider is not None:
                self._render_source_columns()

            if kind == 'Join':
                self._render_join_columns(node_id, join_sides)

            if kind == 'AddColumn':
                self._render_add_column(node_id, upstream_columns)

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

    def _render_source_columns(self):
        """Show the real column names of the selected data source file."""
        ui.separator().classes('my-3')
        with ui.row().classes('w-full items-center justify-between'):
            ui.label('📋 Colonne del file').classes('text-sm font-bold text-gray-700')
            ui.button(icon='refresh', on_click=lambda: refresh()).props('flat dense size=sm').tooltip('Rileggi le colonne')
        container = ui.column().classes('w-full gap-1')
        pending: Dict[str, Any] = {'timer': None}

        def refresh():
            if container.is_deleted:
                return
            container.clear()
            values = {key: (inp.value or '') for key, inp in self.field_inputs.items()}
            with container:
                if not str(values.get('file_path') or '').strip():
                    ui.label('Seleziona un file per vedere le colonne.').classes('text-xs text-gray-400 italic')
                    return
                try:
                    columns = list(self.source_columns_provider(values))
                except FileNotFoundError as err:
                    ui.label(f'File non trovato: {err}').classes('text-xs text-orange-700')
                    return
                except Exception as err:  # noqa: BLE001 - show the reason to the user
                    ui.label(f'Impossibile leggere le colonne: {err}').classes('text-xs text-red-600')
                    return
                if not columns:
                    ui.label('Nessuna colonna trovata nel file.').classes('text-xs text-gray-400 italic')
                    return
                ui.label(f'{len(columns)} colonne disponibili').classes('text-xs text-gray-500')
                with ui.row().classes('gap-1 flex-wrap'):
                    for column in columns:
                        ui.badge(column).props('outline color=primary')

        def schedule_refresh():
            timer = pending.get('timer')
            if timer is not None:
                try:
                    timer.cancel()
                except Exception:  # noqa: BLE001 - the timer may already be gone
                    pass
            pending['timer'] = ui.timer(0.4, refresh, once=True, immediate=False)

        for key in ('source_type', 'file_path', 'csv_separator', 'query'):
            inp = self.field_inputs.get(key)
            if inp is not None:
                inp.on_value_change(lambda _: schedule_refresh())
        refresh()

    def _render_join_columns(self, node_id: Optional[str], sides: List[Tuple[str, List[str]]]):
        """Show the columns available on each side of a Join node."""
        ui.separator().classes('my-3')
        ui.label('🔗 Colonne disponibili per la join').classes('text-sm font-bold text-gray-700 mb-1')
        if not node_id:
            ui.label(
                'Connetti due input a questo nodo Join e riapri il pannello per scegliere le colonne dagli elenchi.'
            ).classes('text-xs text-orange-700')
            return
        if not sides or not any(columns for _, columns in sides):
            ui.label(
                'Impossibile leggere le colonne degli input: verifica che i due Data Source siano collegati '
                'e che i file esistano.'
            ).classes('text-xs text-orange-700')
            return

        for title, columns in sides:
            with ui.column().classes('w-full gap-1 q-mb-sm'):
                ui.label(title).classes('text-xs font-semibold text-gray-600')
                if not columns:
                    ui.label('Nessuna colonna disponibile.').classes('text-xs text-gray-400 italic')
                    continue
                with ui.row().classes('gap-1 flex-wrap'):
                    for column in columns:
                        ui.badge(column).props('outline color=primary')

    def _render_add_column(self, node_id: Optional[str], upstream_columns: List[str]):
        """Show upstream columns and a live preview of the calculated values."""
        ui.separator().classes('my-3')
        ui.label('🧮 Colonna calcolata').classes('text-sm font-bold text-gray-700 mb-1')

        if not node_id:
            ui.label(
                'Aggiungi il nodo e collegalo a una tabella per vedere le colonne disponibili e l\'anteprima.'
            ).classes('text-xs text-orange-700')
        elif not upstream_columns:
            ui.label(
                'Nessuna colonna disponibile: collega questo nodo a un Data Source (o a un nodo a valle) '
                'per scegliere i campi.'
            ).classes('text-xs text-orange-700')
        else:
            ui.label(f"{len(upstream_columns)} colonne disponibili nell'input").classes('text-xs text-gray-500')
            with ui.row().classes('gap-1 flex-wrap q-mb-sm'):
                for column in upstream_columns:
                    ui.badge(column).props('outline color=primary')

        preview = ui.column().classes('w-full gap-1')

        sample = None
        if node_id and self.sample_frame_provider is not None:
            try:
                sample = self.sample_frame_provider(node_id)
            except Exception:  # noqa: BLE001 - the preview must never break the panel
                sample = None

        def current_config() -> Dict[str, Any]:
            def value_of(key: str, default: Any) -> Any:
                inp = self.field_inputs.get(key)
                return default if inp is None else inp.value

            return {
                'new_column': value_of('new_column', ''),
                'mode': value_of('mode', 'concat') or 'concat',
                'columns': value_of('columns', []),
                'separator': value_of('separator', '_'),
                'trim': value_of('trim', True),
                'expression': value_of('expression', ''),
            }

        def refresh():
            if preview.is_deleted:
                return
            preview.clear()
            vals = current_config()
            new_column = str(vals['new_column'] or '').strip()
            columns = as_list(vals['columns'])
            with preview:
                if not new_column:
                    ui.label('Scegli il nome della nuova colonna.').classes('text-xs text-gray-400 italic')
                    return
                try:
                    sql = build_calculated_expression(
                        mode=vals['mode'],
                        columns=columns,
                        separator=vals['separator'],
                        expression=vals['expression'],
                        trim=bool(vals['trim']),
                    )
                except ValueError as err:
                    ui.label(str(err)).classes('text-xs text-orange-700')
                    return
                ui.label(f'{new_column} = {sql}').classes(
                    'text-xs font-mono text-gray-700 bg-white border rounded p-1'
                ).style('word-break: break-all;')

                if sample is None or len(sample) == 0:
                    ui.label(
                        "Anteprima non disponibile: collega l'input o esegui la pipeline per verificare i valori."
                    ).classes('text-xs text-gray-400 italic')
                    return
                try:
                    result = apply_calculated_column(
                        sample,
                        new_column,
                        mode=vals['mode'],
                        columns=columns,
                        separator=vals['separator'],
                        expression=vals['expression'],
                        trim=bool(vals['trim']),
                    )
                except Exception as err:  # noqa: BLE001 - show the SQL error to the user
                    ui.label(f'Anteprima non disponibile: {err}').classes('text-xs text-red-600')
                    return

                is_expression = (vals['mode'] or 'concat') == 'expression'
                ui.label('Prime righe (valori calcolati):').classes('text-xs font-semibold text-gray-600 q-mt-xs')
                for row in result.head(3).iter_rows(named=True):
                    parts = []
                    if not is_expression:
                        parts = [f'{column}={row.get(column)!r}' for column in columns]
                    value = row.get(new_column)
                    prefix = ' | '.join(parts)
                    label = f'{prefix}  →  {new_column}={value!r}' if prefix else f'{new_column}={value!r}'
                    ui.label(label).classes('text-xs font-mono text-gray-700')

        def sync_visibility():
            mode_input = self.field_inputs.get('mode')
            is_expression = ((mode_input.value if mode_input is not None else 'concat') or 'concat') == 'expression'
            for key in ('columns', 'separator', 'trim'):
                inp = self.field_inputs.get(key)
                if inp is not None:
                    inp.set_visibility(not is_expression)
            expr = self.field_inputs.get('expression')
            if expr is not None:
                expr.set_visibility(is_expression)

        pending: Dict[str, Any] = {'timer': None}

        def schedule_refresh():
            sync_visibility()
            timer = pending.get('timer')
            if timer is not None:
                try:
                    timer.cancel()
                except Exception:  # noqa: BLE001 - the timer may already be gone
                    pass
            pending['timer'] = ui.timer(0.3, refresh, once=True, immediate=False)

        for key in ('new_column', 'mode', 'columns', 'separator', 'trim', 'expression'):
            inp = self.field_inputs.get(key)
            if inp is not None and hasattr(inp, 'on_value_change'):
                inp.on_value_change(lambda _: schedule_refresh())
        sync_visibility()
        refresh()

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
