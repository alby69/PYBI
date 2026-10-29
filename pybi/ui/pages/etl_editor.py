"""Power Query Editor page implementation with Applied Steps and interactive data grid."""

import copy
import json
from typing import Any, Dict, List, Optional

from nicegui import ui
import polars as pl

from pybi.core.history import HistoryManager
from pybi.core.storage import default_storage
from pybi.dashboard.binding import default_binder
from pybi.etl.executor import ETLExecutor, execute_linear_etl
from pybi.ui.components.navbar import render_navbar
from pybi.ui.components.project_manager import ProjectManager
from pybi.ui.shortcuts import render_shortcuts_help_button
from pybi.ui.table_utils import build_preview_table
from pybi.ui.theme import default_theme


def create_etl_editor_page():
    render_navbar(active='/etl-editor')
    with ui.row().classes('w-full items-center justify-between q-mt-sm'):
        with ui.column().classes('gap-0'):
            ui.label('Power Query Editor - Visual Data Transformation').classes('text-2xl font-bold q-mb-xs')
            ui.label('Transforms single-table data sources sequentially using Applied Steps, column actions, and interactive preview.').classes('text-gray-600 q-mb-md')
        ui.button(
            'Apri nuovo Power Query Editor',
            icon='auto_awesome',
            on_click=lambda: ui.navigate.to('/power-query')
        ).props('color=primary')

    # Per-table applied steps dictionary & current source table state
    applied_steps_by_table: Dict[str, List[Dict[str, Any]]] = {
        "sales_data.csv": [
            {
                "id": "step_1",
                "name": "Righe filtrate (region = 'EU')",
                "operation": "filter",
                "params": {"condition": "region = 'EU'"}
            }
        ]
    }
    current_source_table: str = "sales_data.csv"

    # State variables
    query_state = {
        "query_name": "Sales_Data",
        "source": {"type": "csv", "path": current_source_table},
        "steps": copy.deepcopy(applied_steps_by_table["sales_data.csv"])
    }
    active_step_index = len(query_state["steps"])  # 0 = Origine, 1..N = Step N
    active_df: Optional[pl.DataFrame] = None
    history = HistoryManager()

    def record_history():
        history.push_state(copy.deepcopy(query_state))

    def project_data_dir():
        try:
            return default_storage.get_project_data_dir(project_manager.project_id)
        except Exception:
            return None

    # --- Project switch handler ----------------------------------------------------
    def handle_project_switch(pid, action):
        nonlocal current_source_table
        if action == 'create':
            current_source_table = "sales_data.csv"
            applied_steps_by_table.clear()
            applied_steps_by_table["sales_data.csv"] = [
                {
                    "id": "step_1",
                    "name": "Righe filtrate (region = 'EU')",
                    "operation": "filter",
                    "params": {"condition": "region = 'EU'"}
                }
            ]
            query_state["query_name"] = "Sales_Data"
            query_state["source"] = {"type": "csv", "path": current_source_table}
            query_state["steps"] = copy.deepcopy(applied_steps_by_table["sales_data.csv"])
            save_pipeline(notify=False)
            log_container.push(f'[Project] Created "{pid}" with sample query.')
            ui.notify(f'Progetto "{pid}" creato.', type='positive')
            status_label.set_text(f'State: New project "{pid}"')
            refresh_file_list()
            update_preview()
            return

        if default_storage.project_exists(pid):
            load_pipeline(notify=False)
            status_label.set_text(f'State: Switched to "{pid}"')
        else:
            status_label.set_text(f'State: "{pid}" has no saved query yet')
        refresh_file_list()

    # --- File Upload & Management --------------------------------------------------
    async def handle_upload(e):
        pid = project_manager.project_id
        if not pid:
            ui.notify('Seleziona o crea prima un progetto.', type='warning')
            return

        try:
            content = await e.file.read()
            file_path = default_storage.save_uploaded_file(pid, e.file.name, content)
            log_container.push(f'[Upload] File "{e.file.name}" salvato in: {file_path}')
            ui.notify(f'File "{e.file.name}" caricato con successo!', type='positive')
            refresh_file_list()
            # Set as current source table
            update_source(e.file.name)
        except Exception as err:
            ui.notify(f'Errore durante il caricamento: {err}', type='negative')

    def refresh_file_list():
        pid = project_manager.project_id
        file_list_container.clear()
        if not pid:
            return
        files = default_storage.list_project_files(pid)
        source_select.options = get_source_options()
        with file_list_container:
            if not files:
                ui.label('Nessun file presente. Carica un file per iniziare.').classes('text-sm text-gray-500 italic')
            else:
                for f in files:
                    with ui.row().classes('w-full items-center gap-2 q-pa-xs'):
                        ui.icon('insert_drive_file', color='primary')
                        ui.label(f).classes('text-sm flex-grow').style('word-break: break-all;')
                        ui.button(
                            icon='delete',
                            on_click=lambda fn=f: delete_file(fn)
                        ).props('color=negative flat size=sm dense').tooltip('Elimina file')

    def delete_file(filename: str):
        pid = project_manager.project_id
        if default_storage.delete_project_file(pid, filename):
            ui.notify(f'File "{filename}" eliminato.', type='positive')
            if filename in applied_steps_by_table:
                del applied_steps_by_table[filename]
            refresh_file_list()
        else:
            ui.notify(f'Impossibile eliminare "{filename}".', type='negative')

    # --- Top Bar & Project Manager ------------------------------------------------
    with ui.row().classes('w-full items-center gap-4 q-mb-sm'):
        project_manager = ProjectManager(value='default', on_switch=handle_project_switch)
        ui.space()
        status_label = ui.label('State: Ready').classes('text-sm font-semibold text-blue-700')

    # --- Header A: Query Controls & Toolbar ----------------------------------------
    with ui.card().classes('w-full q-mb-md p-3 bg-slate-50 border border-slate-200'):
        with ui.row().classes('w-full items-center gap-4 flex-wrap'):
            # Query Name
            query_name_input = ui.input(
                label='Nome Query',
                value=query_state["query_name"],
                on_change=lambda e: update_query_name(e.value)
            ).classes('w-48').props('dense outlined')

            # Data Source Selector
            def get_source_options():
                pid = project_manager.project_id
                files = default_storage.list_project_files(pid) if pid else []
                options = ['sales_data.csv'] + [f for f in files if f != 'sales_data.csv']
                return options

            source_select = ui.select(
                options=get_source_options(),
                value=current_source_table,
                label='Origine Dati',
                on_change=lambda e: update_source(e.value)
            ).classes('w-60').props('dense outlined')

            ui.space()

            # Action Buttons
            ui.button('Esegui Query', on_click=lambda: run_pipeline()).props('color=primary icon=play_arrow dense')
            ui.button('Salva Query', on_click=lambda: save_pipeline()).props('color=positive icon=save dense')
            ui.button('Carica Query', on_click=lambda: load_pipeline()).props('color=info icon=folder_open dense')
            ui.button('Reset', on_click=lambda: reset_pipeline()).props('color=secondary icon=refresh dense')
            ui.separator().props('vertical')
            ui.button(icon='undo', on_click=lambda: apply_undo()).props('flat dense').tooltip('Undo (Ctrl+Z)')
            ui.button(icon='redo', on_click=lambda: apply_redo()).props('flat dense').tooltip('Redo (Ctrl+Y)')
            ui.button('JSON', on_click=lambda: open_advanced_editor()).props('flat icon=code dense').tooltip('Advanced Editor (JSON)')
            render_shortcuts_help_button()
            default_theme.render_toggle_button()

        # Transformation Quick Bar
        with ui.row().classes('w-full items-center gap-2 q-mt-sm pt-2 border-t border-slate-200 flex-wrap'):
            ui.label('Trasformazioni Rapide:').classes('text-xs font-bold text-gray-500 q-mr-sm')
            ui.button('Filtra Righe', on_click=lambda: open_filter_dialog()).props('dense outline size=sm icon=filter_alt')
            ui.button('Rinomina Colonna', on_click=lambda: open_rename_dialog()).props('dense outline size=sm icon=edit')
            ui.button('Modifica Tipo', on_click=lambda: open_cast_dialog()).props('dense outline size=sm icon=type_specimen')
            ui.button('Rimuovi Colonna', on_click=lambda: open_remove_column_dialog()).props('dense outline size=sm icon=delete')
            ui.button('Aggiungi Colonna', on_click=lambda: open_add_column_dialog()).props('dense outline size=sm icon=add_circle')
            ui.button('Colonna Condizionale', on_click=lambda: open_conditional_dialog()).props('dense outline size=sm icon=alt_route')
            ui.button('Formatta Testo', on_click=lambda: open_text_format_dialog()).props('dense outline size=sm icon=text_fields')
            ui.button('Rimuovi Duplicati', on_click=lambda: open_dedup_dialog()).props('dense outline size=sm icon=content_copy')

    # --- Gestione File Dati Progetto (Accordion) ------------------------------------
    with ui.expansion('📁 Gestione File Dati Progetto', icon='folder').classes('w-full q-mb-sm'):
        ui.label('Carica file (CSV, Parquet, SQLite) nella cartella data del progetto corrente.').classes('text-xs text-gray-600 q-mb-xs')
        with ui.row().classes('w-full items-center gap-4'):
            ui.upload(
                on_upload=handle_upload,
                label='Carica File Data Source',
                auto_upload=True,
                multiple=False
            ).props('accept=.csv,.parquet,.json,.sqlite').classes('flex-grow')

        with ui.column().classes('w-full q-mt-xs'):
            file_list_container = ui.column().classes('w-full')

    refresh_file_list()

    # --- Central Split-View: Data Grid (Left 3/4) + Applied Steps (Right 1/4) ------
    with ui.row().classes('w-full gap-4 items-start q-mb-md'):
        # Left Panel: Data Grid with horizontal and vertical overflow scrolling
        with ui.card().classes('flex-grow p-4 min-h-[450px] shadow-sm border border-slate-200 overflow-x-auto overflow-y-auto min-w-0').style('width: 72%'):
            with ui.row().classes('w-full items-center justify-between q-mb-xs'):
                preview_status_label = ui.label('Anteprima Dati').classes('font-bold text-base text-slate-800')
                rows_count_label = ui.label('').classes('text-xs font-semibold text-slate-500 bg-slate-100 px-2 py-1 rounded')

            grid_container = ui.column().classes('w-full overflow-x-auto min-h-[360px]').style('overflow-x: auto; overflow-y: auto; min-width: 100%;')

        # Right Panel: Applied Steps (Passaggi Applicati per Tabella)
        with ui.card().classes('p-4 shadow-sm border border-slate-200 bg-slate-50 min-h-[450px]').style('width: 26%'):
            ui.label('📋 Passaggi Applicati').classes('font-bold text-base text-slate-800 q-mb-xs')
            ui.label('Clicca su un passaggio per visualizzare l\'anteprima a quel punto.').classes('text-xs text-gray-500 q-mb-sm')
            steps_list_container = ui.column().classes('w-full gap-2')

    # --- Log & Execution Console ----------------------------------------------------
    with ui.card().classes('w-full p-3 bg-slate-900 text-green-400 font-mono text-xs'):
        ui.label('Console Log Esecuzione ETL').classes('font-bold text-slate-300 text-xs q-mb-xs')
        log_container = ui.log(max_lines=20).classes('w-full h-28 bg-slate-950 font-mono text-xs')
        log_container.push('Power Query Editor inizializzato. Seleziona una sorgente o applica trasformazioni.')

    # ===============================================================================
    # Helper Functions & Event Handlers
    # ===============================================================================

    def update_query_name(name: str):
        query_state["query_name"] = name or "Sales_Data"
        status_label.set_text(f'State: Query name set to "{query_state["query_name"]}"')

    def update_source(filepath: str):
        nonlocal current_source_table
        if not filepath:
            return

        # Save current table steps before switching
        if current_source_table:
            applied_steps_by_table[current_source_table] = copy.deepcopy(query_state.get("steps", []))

        current_source_table = filepath
        source_select.value = current_source_table

        # Load or initialize steps for the selected table
        table_steps = applied_steps_by_table.get(current_source_table, [])
        query_state["source"] = {"type": "csv" if not filepath.endswith(".parquet") else "parquet", "path": filepath}
        query_state["steps"] = copy.deepcopy(table_steps)

        record_history()
        log_container.push(f'[Source] Selezionata tabella sorgente: {filepath}')
        update_preview(step_idx=len(query_state["steps"]))

    def apply_undo():
        prev = history.undo()
        if prev:
            query_state.clear()
            query_state.update(prev)
            query_name_input.value = query_state.get("query_name", "Sales_Data")
            log_container.push('[Undo] Ripristinato stato precedente.')
            update_preview()

    def apply_redo():
        nxt = history.redo()
        if nxt:
            query_state.clear()
            query_state.update(nxt)
            query_name_input.value = query_state.get("query_name", "Sales_Data")
            log_container.push('[Redo] Ripristinato stato successivo.')
            update_preview()

    def update_preview(step_idx: Optional[int] = None):
        nonlocal active_step_index, active_df
        if step_idx is not None:
            active_step_index = step_idx
        else:
            active_step_index = len(query_state["steps"])

        executor = ETLExecutor(duckdb_conn=default_binder.duckdb_conn, base_dir=project_data_dir())
        res = executor.execute_linear_etl(query_state, stop_at_step_index=active_step_index)

        if res.status != "success":
            log_container.push(f'[Error] Esecuzione fallita: {res.error}')
            ui.notify(f'Errore esecuzione: {res.error}', type='negative')
            grid_container.clear()
            with grid_container:
                ui.label(f'Errore anteprima: {res.error}').classes('text-red-600 font-bold p-4')
            return

        # Fetch output dataframe at active step
        step_key = f"step_{active_step_index}" if active_step_index > 0 else "source"
        active_df = res.dataframes.get(step_key)
        if active_df is None and res.output_tables:
            active_df = list(res.output_tables.values())[0]

        render_data_grid(active_df)
        render_applied_steps_panel()

    def render_data_grid(df: Optional[pl.DataFrame]):
        grid_container.clear()
        if df is None or len(df) == 0:
            with grid_container:
                ui.label('Nessun dato da visualizzare').classes('text-gray-400 italic p-4')
            rows_count_label.set_text('0 righe')
            return

        rows_count_label.set_text(f'{len(df)} righe | {len(df.columns)} colonne')

        step_title = "Origine Dati" if active_step_index == 0 else query_state["steps"][active_step_index - 1]["name"]
        preview_status_label.set_text(f'Anteprima ({current_source_table}): {step_title}')

        table_args = build_preview_table(df.head(1000))

        # Render custom interactive header controls above or inside NiceGUI table
        with grid_container:
            # Header column action chips - non-wrapping single row with horizontal overflow scroll
            with ui.row().classes('w-full gap-2 items-center q-mb-xs flex-nowrap overflow-x-auto bg-slate-100 p-2 rounded border border-slate-200').style('white-space: nowrap; overflow-x: auto; min-width: 100%;'):
                ui.label('Azioni Colonna:').classes('text-xs font-bold text-slate-600 flex-shrink-0')
                for col_name in df.columns:
                    col_type_str = str(df[col_name].dtype)
                    with ui.button(f'{col_name} ({col_type_str})').props('dense outline size=xs icon-right=arrow_drop_down color=slate').classes('lowercase flex-shrink-0').style('white-space: nowrap;'):
                        with ui.menu():
                            ui.menu_item(f'Rinomina "{col_name}"', on_click=lambda c=col_name: open_rename_dialog(c))
                            ui.menu_item('Modifica Tipo...', on_click=lambda c=col_name: open_cast_dialog(c))
                            ui.menu_item(f'Rimuovi "{col_name}"', on_click=lambda c=col_name: add_step("remove_column", f"Rimuovi {c}", {"column": c}))
                            ui.menu_item(f'Rimuovi Altre Colonne', on_click=lambda c=col_name: add_step("remove_other_columns", f"Mantieni solo {c}", {"keep_columns": [c]}))
                            ui.menu_item('Sostituisci Valori...', on_click=lambda c=col_name: open_replace_dialog(c))
                            ui.menu_item('Filtra per Colonna...', on_click=lambda c=col_name: open_filter_dialog(c))

            # Table preview container with horizontal scrolling
            with ui.element('div').classes('w-full overflow-x-auto').style('overflow-x: auto; min-width: 100%;'):
                if table_args['row_key']:
                    ui.table(**table_args).classes('w-full font-mono text-xs')
                else:
                    ui.table(columns=table_args['columns'], rows=table_args['rows']).classes('w-full font-mono text-xs')

    def render_applied_steps_panel():
        steps_list_container.clear()
        with steps_list_container:
            # Step 0: Origine
            is_active_0 = (active_step_index == 0)
            bg_cls_0 = 'bg-blue-100 border-blue-500 font-bold' if is_active_0 else 'bg-white hover:bg-slate-100 border-slate-200'
            with ui.card().classes(f'w-full p-2 border cursor-pointer transition-all {bg_cls_0}').on('click', lambda: update_preview(0)):
                with ui.row().classes('w-full items-center justify-between'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('settings', color='primary', size='xs')
                        ui.label(f'Origine ({current_source_table})').classes('text-xs font-semibold truncate')
                    ui.badge('0', color='primary').props('dense')

            # Steps 1..N
            for idx, step in enumerate(query_state["steps"], start=1):
                is_active = (active_step_index == idx)
                bg_cls = 'bg-blue-100 border-blue-500 font-bold' if is_active else 'bg-white hover:bg-slate-100 border-slate-200'
                step_op = step.get("operation", "step")

                # Operation icon
                icon_name = 'tune'
                if step_op == 'filter':
                    icon_name = 'filter_alt'
                elif 'rename' in step_op:
                    icon_name = 'edit'
                elif 'cast' in step_op or 'type' in step_op:
                    icon_name = 'type_specimen'
                elif 'add' in step_op or 'custom' in step_op:
                    icon_name = 'add_circle'
                elif 'remove' in step_op or 'drop' in step_op:
                    icon_name = 'delete'
                elif 'text' in step_op or 'format' in step_op:
                    icon_name = 'text_fields'

                with ui.card().classes(f'w-full p-2 border cursor-pointer transition-all {bg_cls}').on('click', lambda i=idx: update_preview(i)):
                    with ui.row().classes('w-full items-center justify-between gap-1'):
                        with ui.row().classes('items-center gap-2 flex-grow overflow-hidden'):
                            ui.icon(icon_name, color='secondary', size='xs')
                            ui.label(step.get("name", f"Passaggio {idx}")).classes('text-xs font-medium truncate')
                        ui.button(
                            icon='close',
                            on_click=lambda i=idx: remove_step(i)
                        ).props('flat dense size=xs color=negative').tooltip('Elimina passaggio')

    def add_step(operation: str, name: str, params: Dict[str, Any]):
        record_history()
        new_step_id = f"step_{len(query_state['steps']) + 1}"
        new_step = {
            "id": new_step_id,
            "name": name,
            "operation": operation,
            "params": params,
        }
        query_state["steps"].append(new_step)
        if current_source_table:
            applied_steps_by_table[current_source_table] = copy.deepcopy(query_state["steps"])

        log_container.push(f'[Step Aggiunto ({current_source_table})] {name} ({operation})')
        status_label.set_text('State: Modified, save to persist')
        update_preview(step_idx=len(query_state["steps"]))

    def remove_step(step_idx: int):
        record_history()
        if 1 <= step_idx <= len(query_state["steps"]):
            removed = query_state["steps"].pop(step_idx - 1)
            if current_source_table:
                applied_steps_by_table[current_source_table] = copy.deepcopy(query_state["steps"])
            log_container.push(f'[Step Rimosso ({current_source_table})] {removed.get("name")}')
        new_idx = min(step_idx - 1, len(query_state["steps"]))
        update_preview(step_idx=new_idx)

    # ===============================================================================
    # Transformation Dialogs
    # ===============================================================================

    def open_filter_dialog(prefill_col: str = ''):
        cols = active_df.columns if active_df is not None else []
        d = ui.dialog()
        with d, ui.card().classes('w-96 p-4'):
            ui.label('Filtra Righe').classes('font-bold text-lg q-mb-xs')
            col_sel = ui.select(options=cols, value=prefill_col or (cols[0] if cols else ''), label='Colonna').classes('w-full')
            op_sel = ui.select(options=['==', '!=', '>', '<', '>=', '<='], value='==', label='Operatore').classes('w-full')
            val_in = ui.input(label='Valore').classes('w-full')

            with ui.row().classes('w-full justify-end gap-2 q-mt-md'):
                ui.button('Annulla', on_click=d.close).props('flat')
                def apply_f():
                    c, op, v = col_sel.value, op_sel.value, val_in.value
                    if c and v:
                        v_str = f"'{v}'" if not v.isdigit() else v
                        cond = f"{c} {op} {v_str}"
                        add_step("filter", f"Filtra {c} {op} {v}", {"condition": cond, "column": c, "operator": op, "value": v})
                        d.close()
                ui.button('Applica', on_click=apply_f).props('color=primary')
        d.open()

    def open_rename_dialog(prefill_col: str = ''):
        cols = active_df.columns if active_df is not None else []
        d = ui.dialog()
        with d, ui.card().classes('w-96 p-4'):
            ui.label('Rinomina Colonna').classes('font-bold text-lg q-mb-xs')
            col_sel = ui.select(options=cols, value=prefill_col or (cols[0] if cols else ''), label='Colonna Attuale').classes('w-full')
            new_name_in = ui.input(label='Nuovo Nome').classes('w-full')

            with ui.row().classes('w-full justify-end gap-2 q-mt-md'):
                ui.button('Annulla', on_click=d.close).props('flat')
                def apply_r():
                    old_c, new_c = col_sel.value, new_name_in.value.strip()
                    if old_c and new_c:
                        add_step("rename_column", f"Rinomina '{old_c}' -> '{new_c}'", {"mapping": {old_c: new_c}})
                        d.close()
                ui.button('Applica', on_click=apply_r).props('color=primary')
        d.open()

    def open_cast_dialog(prefill_col: str = ''):
        cols = active_df.columns if active_df is not None else []
        d = ui.dialog()
        with d, ui.card().classes('w-96 p-4'):
            ui.label('Modifica Tipo Dati').classes('font-bold text-lg q-mb-xs')
            col_sel = ui.select(options=cols, value=prefill_col or (cols[0] if cols else ''), label='Colonna').classes('w-full')
            type_sel = ui.select(options=['text', 'int', 'float', 'date', 'boolean'], value='text', label='Tipo Destinazione').classes('w-full')

            with ui.row().classes('w-full justify-end gap-2 q-mt-md'):
                ui.button('Annulla', on_click=d.close).props('flat')
                def apply_c():
                    c, t = col_sel.value, type_sel.value
                    if c and t:
                        add_step("cast_column", f"Cambia tipo '{c}' -> {t}", {"casts": {c: t}})
                        d.close()
                ui.button('Applica', on_click=apply_c).props('color=primary')
        d.open()

    def open_remove_column_dialog():
        cols = active_df.columns if active_df is not None else []
        d = ui.dialog()
        with d, ui.card().classes('w-96 p-4'):
            ui.label('Rimuovi Colonna').classes('font-bold text-lg q-mb-xs')
            col_sel = ui.select(options=cols, value=cols[0] if cols else '', label='Seleziona Colonna').classes('w-full')

            with ui.row().classes('w-full justify-end gap-2 q-mt-md'):
                ui.button('Annulla', on_click=d.close).props('flat')
                def apply_rm():
                    c = col_sel.value
                    if c:
                        add_step("remove_column", f"Rimuovi colonna '{c}'", {"column": c})
                        d.close()
                ui.button('Rimuovi', on_click=apply_rm).props('color=negative')
        d.open()

    def open_add_column_dialog():
        cols = active_df.columns if active_df is not None else []
        d = ui.dialog()
        with d, ui.card().classes('w-[550px] max-w-full p-4'):
            ui.label('Aggiungi Colonna Personalizzata').classes('font-bold text-lg q-mb-xs')
            new_col_in = ui.input(
                label='Nome Nuova Colonna',
                value='nuova_colonna',
                placeholder='nuova_colonna'
            ).classes('w-full').props('outlined dense')

            expr_in = ui.input(
                label='Espressione SQL / Formula',
                value='',
                placeholder='es. amount * 1.2 oppure NomeClienteSped || \'_\' || CittaClienteSped'
            ).classes('w-full q-mt-xs').props('outlined dense')

            ui.label(f'Colonne disponibili: {", ".join(cols)}').classes('text-xs text-slate-500 q-mt-xs font-mono')

            # Expandable Interactive Help Guide (Task 1.3)
            with ui.expansion('💡 Guida & Esempi Espressioni SQL', icon='help_outline').classes('w-full q-mt-sm bg-slate-50 border rounded text-xs'):
                with ui.column().classes('p-2 gap-2 text-slate-700'):
                    ui.label('💡 Esempi Pratici').classes('font-bold text-slate-900')
                    ui.markdown(
                        "- **Concatenazione**: `CONCAT(NomeClienteSped, '_', CittaClienteSped)` oppure `NomeClienteSped || '_' || CittaClienteSped`\n"
                        "- **Matematica**: `prezzo * 1.22`\n"
                        "- **Condizionale**: `CASE WHEN stato = 'OK' THEN 'Valido' ELSE 'Errore' END`"
                    ).classes('text-xs text-slate-800')

                    ui.label('📚 Funzioni Supportate (DuckDB/SQL)').classes('font-bold text-slate-900 q-mt-xs')
                    ui.markdown(
                        "- **Stringa**: `CONCAT()`, `UPPER()`, `LOWER()`, `SUBSTRING()`, `LENGTH()`, `TRIM()`\n"
                        "- **Numerica**: `ROUND()`, `ABS()`, `CEIL()`, `FLOOR()`\n"
                        "- **Logica / Null**: `COALESCE()`, `NULLIF()`, `CASE WHEN ... THEN ... END`"
                    ).classes('text-xs text-slate-800')

            with ui.row().classes('w-full justify-end gap-2 q-mt-md'):
                ui.button('Annulla', on_click=d.close).props('flat')
                def apply_add():
                    nc, expr = new_col_in.value.strip(), expr_in.value.strip()
                    if nc and expr:
                        add_step("add_column", f"Aggiungi colonna '{nc}'", {"new_column": nc, "mode": "expression", "expression": expr})
                        d.close()
                ui.button('Aggiungi', on_click=apply_add).props('color=primary')
        d.open()

    def open_conditional_dialog():
        cols = active_df.columns if active_df is not None else []
        d = ui.dialog()
        with d, ui.card().classes('w-[450px] p-4'):
            ui.label('Aggiungi Colonna Condizionale').classes('font-bold text-lg q-mb-xs')
            new_col_in = ui.input(label='Nome Nuova Colonna', value='categoria_condizionale').classes('w-full')
            if_cond_in = ui.input(label='Condizione IF (es. amount > 100)', value='').classes('w-full')
            then_val_in = ui.input(label='Valore THEN (es. Alto)', value='').classes('w-full')
            else_val_in = ui.input(label='Valore ELSE (es. Basso)', value='').classes('w-full')

            with ui.row().classes('w-full justify-end gap-2 q-mt-md'):
                ui.button('Annulla', on_click=d.close).props('flat')
                def apply_cond():
                    nc = new_col_in.value.strip()
                    if_c = if_cond_in.value.strip()
                    then_v = then_val_in.value.strip()
                    else_v = else_val_in.value.strip()
                    if nc and if_c:
                        add_step("conditional_column", f"Colonna condizionale '{nc}'", {
                            "new_column": nc,
                            "if_condition": if_c,
                            "then_value": then_v,
                            "else_value": else_v
                        })
                        d.close()
                ui.button('Crea', on_click=apply_cond).props('color=primary')
        d.open()

    def open_replace_dialog(prefill_col: str = ''):
        cols = active_df.columns if active_df is not None else []
        d = ui.dialog()
        with d, ui.card().classes('w-96 p-4'):
            ui.label('Sostituisci Valori').classes('font-bold text-lg q-mb-xs')
            col_sel = ui.select(options=cols, value=prefill_col or (cols[0] if cols else ''), label='Colonna').classes('w-full')
            old_val_in = ui.input(label='Valore da Sostituire').classes('w-full')
            new_val_in = ui.input(label='Nuovo Valore').classes('w-full')

            with ui.row().classes('w-full justify-end gap-2 q-mt-md'):
                ui.button('Annulla', on_click=d.close).props('flat')
                def apply_rep():
                    c, ov, nv = col_sel.value, old_val_in.value, new_val_in.value
                    if c and ov is not None and nv is not None:
                        add_step("replace_values", f"Sostituisci in '{c}'", {"column": c, "old_value": ov, "new_value": nv})
                        d.close()
                ui.button('Sostituisci', on_click=apply_rep).props('color=primary')
        d.open()

    def open_text_format_dialog():
        cols = active_df.columns if active_df is not None else []
        d = ui.dialog()
        with d, ui.card().classes('w-96 p-4'):
            ui.label('Formattazione Testo').classes('font-bold text-lg q-mb-xs')
            col_sel = ui.select(options=cols, value=cols[0] if cols else '', label='Colonna').classes('w-full')
            action_sel = ui.select(options=['trim', 'upper', 'lower', 'clean'], value='trim', label='Azione Testo').classes('w-full')

            with ui.row().classes('w-full justify-end gap-2 q-mt-md'):
                ui.button('Annulla', on_click=d.close).props('flat')
                def apply_tf():
                    c, act = col_sel.value, action_sel.value
                    if c and act:
                        add_step("text_transform", f"Formatta {act} '{c}'", {"columns": [c], "action": act})
                        d.close()
                ui.button('Applica', on_click=apply_tf).props('color=primary')
        d.open()

    def open_dedup_dialog():
        cols = active_df.columns if active_df is not None else []
        d = ui.dialog()
        with d, ui.card().classes('w-96 p-4'):
            ui.label('Rimuovi Duplicati').classes('font-bold text-lg q-mb-xs')
            col_sel = ui.select(options=['Tutte le colonne'] + list(cols), value='Tutte le colonne', label='Sub-set Colonne').classes('w-full')

            with ui.row().classes('w-full justify-end gap-2 q-mt-md'):
                ui.button('Annulla', on_click=d.close).props('flat')
                def apply_dd():
                    c = col_sel.value
                    cols_param = [c] if c != 'Tutte le colonne' else []
                    add_step("deduplicate", "Rimuovi duplicati", {"columns": cols_param})
                    d.close()
                ui.button('Rimuovi', on_click=apply_dd).props('color=primary')
        d.open()

    def open_advanced_editor():
        d = ui.dialog()
        with d, ui.card().classes('w-[600px] p-4'):
            ui.label('Advanced Editor - Power Query JSON').classes('font-bold text-lg q-mb-xs')
            json_str = json.dumps(query_state, indent=2)
            editor_area = ui.textarea(value=json_str).classes('w-full font-mono text-xs h-80')

            with ui.row().classes('w-full justify-end gap-2 q-mt-md'):
                ui.button('Annulla', on_click=d.close).props('flat')
                def save_json():
                    try:
                        parsed = json.loads(editor_area.value)
                        query_state.clear()
                        query_state.update(parsed)
                        record_history()
                        query_name_input.value = query_state.get("query_name", "Sales_Data")
                        source_select.value = query_state.get("source", {}).get("path", "sales_data.csv")
                        ui.notify('JSON aggiornato con successo!', type='positive')
                        d.close()
                        update_preview()
                    except Exception as err:
                        ui.notify(f'JSON non valido: {err}', type='negative')
                ui.button('Salva JSON', on_click=save_json).props('color=primary')
        d.open()

    # --- Pipeline Management Actions ----------------------------------------------
    def run_pipeline():
        log_container.push('[Execution] Esecuzione query finale in corso...')
        status_label.set_text('State: Executing pipeline...')

        executor = ETLExecutor(duckdb_conn=default_binder.duckdb_conn, base_dir=project_data_dir())
        res = executor.execute_linear_etl(query_state)

        for l in res.logs:
            log_container.push(f'[Engine] {l}')

        if res.status == 'success':
            for tbl_name, df in res.output_tables.items():
                default_binder.register_source(tbl_name, df)
                log_container.push(f'[Output] Tabella "{tbl_name}" ({len(df)} righe) registrata per i Widget Dashboard.')
            ui.notify(f'Esecuzione completata! Tabella "{query_state["query_name"]}" registrata.', type='positive')
            status_label.set_text('State: Query Succeeded')
        else:
            ui.notify(f'Errore esecuzione: {res.error}', type='negative')
            status_label.set_text(f'State: Execution Failed ({res.error})')

    def save_pipeline(notify=True):
        pid = project_manager.project_id
        default_storage.save_etl_dag(pid, query_state)
        log_container.push(f'[Storage] Salvata query ETL per progetto "{pid}".')
        status_label.set_text(f'State: Query saved to "{pid}"')
        if notify:
            ui.notify(f'Query salvata per il progetto "{pid}"', type='positive')

    def load_pipeline(notify=True):
        pid = project_manager.project_id
        try:
            data = default_storage.load_etl_dag(pid)
            if data and ("steps" in data or "source" in data):
                query_state.clear()
                query_state.update({
                    "query_name": data.get("query_name") or data.get("name") or "Sales_Data",
                    "source": data.get("source") or {"type": "csv", "path": "sales_data.csv"},
                    "steps": data.get("steps") or []
                })
            query_name_input.value = query_state["query_name"]
            src_path = query_state["source"].get("path", "sales_data.csv")
            source_select.value = src_path
            current_source_table = src_path
            applied_steps_by_table[current_source_table] = copy.deepcopy(query_state["steps"])

            log_container.push(f'[Storage] Caricata query ETL per progetto "{pid}".')
            status_label.set_text(f'State: Loaded from "{pid}"')
            if notify:
                ui.notify(f'Query caricata per "{pid}"', type='positive')
            update_preview()
        except Exception as err:
            log_container.push(f'[Storage Error] Impossibile caricare query per "{pid}": {err}')
            if notify:
                ui.notify(f'Impossibile caricare la query: {err}', type='negative')

    def reset_pipeline():
        nonlocal current_source_table
        current_source_table = "sales_data.csv"
        applied_steps_by_table[current_source_table] = []
        query_state["query_name"] = "Sales_Data"
        query_state["source"] = {"type": "csv", "path": current_source_table}
        query_state["steps"] = []
        query_name_input.value = query_state["query_name"]
        source_select.value = current_source_table
        log_container.push('[Reset] Ripristinata query allo stato iniziale.')
        status_label.set_text('State: Reset completed')
        update_preview(step_idx=0)

    # Initial loading when opening page
    if default_storage.project_exists(project_manager.project_id):
        load_pipeline(notify=False)
    else:
        update_preview()
