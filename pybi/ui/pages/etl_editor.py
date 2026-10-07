"""ETL Editor page implementation with node palette, property editor and ETLExecutor."""

import copy

from nicegui import ui

from pybi.core.storage import default_storage
from pybi.dashboard.binding import default_binder
from pybi.etl.executor import execute_dag
from pybi.etl.node_factory import (
    NODE_KINDS,
    build_node,
    new_node_id,
    node_kind,
    validate_pipeline,
)
from pybi.core.history import HistoryManager
from pybi.ui.components.flow_editor import FlowEditor
from pybi.ui.components.project_manager import ProjectManager
from pybi.ui.components.property_panel import PropertyPanel
from pybi.ui.components.search_bar import SearchBar
from pybi.ui.shortcuts import render_shortcuts_help_button
from pybi.ui.theme import NODE_COLORS, default_theme
from pybi.ui.table_utils import build_preview_table

NEW_NODE_X = 80
NEW_NODE_Y_STEP = 90


def create_etl_editor_page():
    ui.label('ETL Editor - Pipeline DAG Builder').classes('text-2xl font-bold q-mb-sm')
    ui.label('Build a pipeline by adding nodes, editing their parameters, then connecting them left to right.').classes('text-gray-600 q-mb-md')

    sample_nodes = [
        {
            'id': 'node_1',
            'type': 'input',
            'label': '📄 CSV Source (sales_data.csv)',
            'position': {'x': 50, 'y': 100},
            'style': {'background': '#e0f2fe', 'border': '2px solid #0284c7', 'borderRadius': '8px', 'padding': '10px'},
            'data': {'node_type': 'DataSource', 'source_type': 'csv', 'file_path': 'sales_data.csv'}
        },
        {
            'id': 'node_2',
            'label': "⚡ Filter Rows (region = 'EU')",
            'position': {'x': 320, 'y': 100},
            'style': {'background': '#fef3c7', 'border': '2px solid #d97706', 'borderRadius': '8px', 'padding': '10px'},
            'data': {'node_type': 'Transform', 'transform_type': 'filter', 'condition': "region = 'EU'"}
        },
        {
            'id': 'node_3',
            'type': 'output',
            'label': '💾 DuckDB Table (filtered_sales)',
            'position': {'x': 600, 'y': 100},
            'style': {'background': '#dcfce7', 'border': '2px solid #16a34a', 'borderRadius': '8px', 'padding': '10px'},
            'data': {'node_type': 'Output', 'table_name': 'filtered_sales'}
        }
    ]

    sample_edges = [
        {'id': 'e1-2', 'source': 'node_1', 'target': 'node_2', 'label': 'raw_stream'},
        {'id': 'e2-3', 'source': 'node_2', 'target': 'node_3', 'label': 'filtered_stream'}
    ]

    def _sample_graph():
        return copy.deepcopy(sample_nodes), copy.deepcopy(sample_edges)

    def handle_project_switch(pid, action):
        if action == 'create':
            nodes, edges = _sample_graph()
            flow.nodes = nodes
            flow.edges = edges
            log_container.push(f'[Project] Created "{pid}" with the sample pipeline.')
            ui.notify(f'Project "{pid}" created with the sample pipeline.', type='positive')
            status_label.set_text(f'State: New project "{pid}"')
            refresh_file_list()
            return
        if action == 'delete':
            load_pipeline(notify=False)
            status_label.set_text(f'State: Switched to "{pid}"')
            refresh_file_list()
            return
        if default_storage.project_exists(pid):
            load_pipeline(notify=False)
            status_label.set_text(f'State: Switched to "{pid}"')
        else:
            nodes, edges = _sample_graph()
            flow.nodes = nodes
            flow.edges = edges
            status_label.set_text(f'State: "{pid}" has no saved pipeline yet')
        refresh_file_list()

    # --- Gestione File Dati Progetto ----------------------------------------------------
    def handle_upload(e):
        pid = project_manager.project_id
        if not pid:
            ui.notify('Seleziona o crea prima un progetto.', type='warning')
            return

        try:
            content = e.content.read() if hasattr(e.content, 'read') else e.content
            file_path = default_storage.save_uploaded_file(pid, e.name, content)
            log_container.push(f'[Upload] File "{e.name}" salvato in: {file_path}')
            ui.notify(f'File "{e.name}" importato con successo!', type='positive')
            refresh_file_list()
        except Exception as err:
            ui.notify(f'Errore durante il salvataggio: {err}', type='negative')

    def refresh_file_list():
        pid = project_manager.project_id
        file_list_container.clear()
        if not pid:
            return
        files = default_storage.list_project_files(pid)
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
            refresh_file_list()
        else:
            ui.notify(f'Impossibile eliminare "{filename}".', type='negative')

    # --- Project bar -------------------------------------------------------
    with ui.row().classes('w-full items-center gap-4 q-mb-md'):
        project_manager = ProjectManager(value='default', on_switch=handle_project_switch)
        ui.space()
        status_label = ui.label('State: Ready').classes('text-sm font-semibold text-blue-700')

    history = HistoryManager()

    def record_history():
        history.push_state({'nodes': copy.deepcopy(flow.nodes), 'edges': copy.deepcopy(flow.edges)})

    def apply_undo():
        prev = history.undo()
        if prev:
            flow.nodes = prev.get('nodes', [])
            flow.edges = prev.get('edges', [])
            log_container.push('[Undo] Restored previous pipeline state.')
            status_label.set_text('State: Undo applied')

    def apply_redo():
        nxt = history.redo()
        if nxt:
            flow.nodes = nxt.get('nodes', [])
            flow.edges = nxt.get('edges', [])
            log_container.push('[Redo] Restored next pipeline state.')
            status_label.set_text('State: Redo applied')

    def get_search_items():
        return [{'id': n.get('id'), 'label': n.get('label'), 'kind': node_kind(n)} for n in flow.nodes]

    def on_search_select(item):
        node_id = item.get('id')
        if node_id:
            found = flow.find_node(node_id)
            if found:
                property_panel.open_node(node_kind(found), node_id, found)

    search_bar = SearchBar(items_provider=get_search_items, on_select=on_search_select)

    # --- Action toolbar ----------------------------------------------------
    with ui.row().classes('w-full gap-2 items-center q-mb-md'):
        ui.button('Execute Pipeline', on_click=lambda: run_pipeline()).props('color=primary icon=play_arrow')
        ui.button('Save Pipeline', on_click=lambda: save_pipeline()).props('color=positive icon=save')
        ui.button('Load Pipeline', on_click=lambda: load_pipeline()).props('color=info icon=folder_open')
        ui.button('Reset Pipeline', on_click=lambda: reset_pipeline()).props('color=secondary icon=refresh')
        ui.separator().props('vertical')
        ui.button(icon='undo', on_click=apply_undo).props('flat dense').tooltip('Undo (Ctrl+Z)')
        ui.button(icon='redo', on_click=apply_redo).props('flat dense').tooltip('Redo (Ctrl+Y)')
        search_bar.render_button()
        render_shortcuts_help_button()
        default_theme.render_toggle_button()

    # --- Gestione File Dati Progetto (UI) -----------------------------------
    with ui.expansion('📁 Gestione File Dati Progetto', icon='folder').classes('w-full q-mb-md'):
        ui.label('Carica file (CSV, Parquet, ecc.) direttamente nella cartella `data` del progetto corrente.').classes('text-sm text-gray-600 q-mb-xs')
        with ui.row().classes('w-full items-center gap-4'):
            ui.upload(
                on_upload=handle_upload,
                label='Seleziona File dal Computer',
                auto_upload=True,
                multiple=False
            ).props('accept=.csv,.parquet,.json,.sqlite').classes('flex-grow')

        with ui.column().classes('w-full q-mt-sm'):
            ui.label('File disponibili per i nodi "Data Source" (usa il percorso relativo o assoluto):').classes('text-sm font-bold q-mb-xs')
            file_list_container = ui.column().classes('w-full')

    # Inizializza la lista al caricamento della pagina
    refresh_file_list()

    # --- Visual Node Palette Card ------------------------------------------
    with ui.card().classes('w-full q-mb-md p-3'):
        ui.label('Add Node').classes('font-bold text-sm q-mb-xs')
        with ui.row().classes('gap-3 flex-wrap items-center'):
            for kind, meta in NODE_KINDS.items():
                col_info = NODE_COLORS.get(kind, {'bg': '#f3f4f6', 'border': '#9ca3af', 'icon': '📌'})
                label_text = f"{col_info['icon']} {meta['label']}"
                ui.button(label_text, on_click=lambda k=kind: property_panel.open_node(k)).props('dense flat').classes('q-px-sm')
        ui.label('Double-click a node on canvas to edit in Property Panel. Drag connector dots to link nodes.').classes('text-xs text-gray-500 q-mt-xs')

    flow = FlowEditor(nodes=copy.deepcopy(sample_nodes), edges=copy.deepcopy(sample_edges)).style('height: 480px; width: 100%;')

    # --- Output preview ----------------------------------------------------
    with ui.card().classes('w-full q-mt-md p-4'):
        ui.label('Pipeline Execution & Output Preview').classes('font-bold text-lg q-mb-xs')
        log_container = ui.log(max_lines=20).classes('w-full h-32 bg-gray-900 text-green-400 font-mono text-xs q-mb-md')
        log_container.push('ETL Flow Editor initialized. Use the palette to add nodes.')
        table_container = ui.column().classes('w-full overflow-x-auto')

    # --- Property Panel callbacks & handlers ------------------------------
    def on_property_save(node_id, kind, values):
        record_history()
        if node_id is None:
            new_id = new_node_id(kind, [n.get('id') for n in flow.nodes])
            node = build_node(kind, values, new_id, {'x': NEW_NODE_X, 'y': 100 + NEW_NODE_Y_STEP * len(flow.nodes)})
            flow.nodes = flow.nodes + [node]
            log_container.push(f'[Node Added] {node["label"]}')
        else:
            index = next((i for i, n in enumerate(flow.nodes) if n.get('id') == node_id), None)
            if index is not None:
                node = build_node(kind, values, node_id, flow.nodes[index].get('position', {}))
                updated = list(flow.nodes)
                updated[index] = node
                flow.nodes = updated
                log_container.push(f'[Node Updated] {node["label"]}')
        status_label.set_text('State: Pipeline modified, save to persist')

    def on_property_delete(node_id):
        record_history()
        removed = next((n for n in flow.nodes if n.get('id') == node_id), None)
        flow.nodes = [n for n in flow.nodes if n.get('id') != node_id]
        flow.edges = [e for e in flow.edges if e.get('source') != node_id and e.get('target') != node_id]
        if removed:
            log_container.push(f'[Node Deleted] {node_id} "{removed.get("label", "")}"')
        status_label.set_text('State: Pipeline modified, save to persist')

    property_panel = PropertyPanel(on_save=on_property_save, on_delete=on_property_delete)

    # --- Canvas event handlers --------------------------------------------
    def handle_node_click(e):
        node = e.args.get('node') or {}
        node_id = node.get('id', 'unknown')
        status_label.set_text(f'State: Node {node_id} selected')

    def handle_node_dbl_click(e):
        node = e.args.get('node') or {}
        node_id = node.get('id')
        if not node_id:
            return
        log_container.push(f'[Node Selected] {node_id} "{node.get("label", "")}"')
        found = flow.find_node(node_id)
        property_panel.open_node(node_kind(found) if found else 'DataSource', node_id, found)

    def handle_node_drag_stop(e):
        record_history()
        node = e.args.get('node', {})
        pos = e.args.get('node', {}).get('position', {})
        log_container.push(f'[Node Moved] Node "{node.get("id", "unknown")}" stopped at x={pos.get("x")}, y={pos.get("y")}')

    def handle_connect(e):
        record_history()
        conn = e.args.get('connection', {})
        log_container.push(f'[Connection Created] Connected {conn.get("source")} -> {conn.get("target")}')
        status_label.set_text(f'State: New connection {conn.get("source")} -> {conn.get("target")}')

    def handle_change(e):
        flow.sync_from_client(e.args.get('nodes', []), e.args.get('edges', []))
        log_container.push(f'[State Updated] Nodes: {len(flow.nodes)}, Edges: {len(flow.edges)}')

    flow.on_node_drag_stop(handle_node_drag_stop)
    flow.on_node_click(handle_node_click)
    flow.on_node_dbl_click(handle_node_dbl_click)
    flow.on_connect(handle_connect)
    flow.on_change(handle_change)

    # --- Pipeline actions --------------------------------------------------
    def render_dataframe(df, caption):
        ui.label(caption).classes('font-semibold text-sm text-gray-800 q-mb-xs')
        table_args = build_preview_table(df)
        if table_args['row_key']:
            ui.table(**table_args).classes('w-full')
        else:
            ui.table(columns=table_args['columns'], rows=table_args['rows']).classes('w-full')

    def run_pipeline():
        problems = validate_pipeline(flow.nodes, flow.edges)
        if problems:
            for problem in problems:
                log_container.push(f'[Validation] {problem}')
            ui.notify(problems[0], type='warning')
            status_label.set_text(f'State: Validation failed ({len(problems)} problems)')
            return

        log_container.push('[Execution] Starting DAG execution engine...')
        status_label.set_text('State: Executing DAG...')

        dag_data = {'nodes': flow.nodes, 'edges': flow.edges}
        result = execute_dag(dag_data, duckdb_conn=default_binder.duckdb_conn)

        for log in result.logs:
            log_container.push(f'[Engine Log] {log}')

        table_container.clear()
        with table_container:
            if result.status != 'success':
                status_label.set_text(f'State: Execution Failed ({result.error})')
                ui.notify(f'Execution Error: {result.error}', type='negative')
                return

            if result.output_tables:
                for tbl_name, df in result.output_tables.items():
                    default_binder.register_source(tbl_name, df)
                    render_dataframe(df, f'Output Table: {tbl_name} ({len(df)} rows) - available to Dashboard widgets')
            elif result.dataframes:
                last_node_id = list(result.dataframes.keys())[-1]
                render_dataframe(result.dataframes[last_node_id], f'Node Output: {last_node_id} ({len(result.dataframes[last_node_id])} rows)')

        status_label.set_text('State: Execution Succeeded')

    def save_pipeline():
        pid = project_manager.project_id
        dag_data = {'nodes': flow.nodes, 'edges': flow.edges}
        default_storage.save_etl_dag(pid, dag_data)
        log_container.push(f'[Storage] Saved ETL DAG for project "{pid}".')
        status_label.set_text(f'State: Pipeline saved to "{pid}"')
        ui.notify(f'Pipeline saved for project "{pid}"', type='positive')
        project_manager.refresh()

    def load_pipeline(notify=True):
        pid = project_manager.project_id
        try:
            dag_data = default_storage.load_etl_dag(pid)
            flow.nodes = dag_data.get('nodes', [])
            flow.edges = dag_data.get('edges', [])
            log_container.push(f'[Storage] Loaded ETL DAG for project "{pid}".')
            status_label.set_text(f'State: Pipeline loaded from "{pid}"')
            if notify:
                ui.notify(f'Pipeline loaded for project "{pid}"', type='positive')
        except Exception as e:
            log_container.push(f'[Storage Error] Could not load project "{pid}": {e}')
            if notify:
                ui.notify(f'Failed to load project: {e}', type='negative')

    def reset_pipeline():
        nodes, edges = _sample_graph()
        flow.nodes = nodes
        flow.edges = edges
        table_container.clear()
        log_container.push('[Reset] Pipeline restored to initial state.')
        status_label.set_text('State: Reset completed')

    if default_storage.project_exists(project_manager.project_id):
        load_pipeline(notify=False)
        log_container.push(f'[Storage] Pipeline for "{project_manager.project_id}" restored on open.')
