"""ETL Editor page implementation with node palette, property editor and ETLExecutor."""

import copy

from nicegui import ui

from pybi.core.storage import default_storage
from pybi.dashboard.binding import default_binder
from pybi.etl.executor import execute_dag
from pybi.etl.node_factory import (
    NODE_KINDS,
    build_node,
    build_node_data,
    default_values,
    fields_for,
    new_node_id,
    node_kind,
    node_values,
    palette_entry,
    validate_pipeline,
)
from pybi.ui.components.flow_editor import FlowEditor
from pybi.ui.components.project_manager import ProjectManager
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

    editing = {'node_id': None}
    rendering = {'form': False}

    def handle_project_switch(pid, action):
        if action == 'create':
            nodes, edges = _sample_graph()
            flow.nodes = nodes
            flow.edges = edges
            log_container.push(f'[Project] Created "{pid}" with the sample pipeline.')
            ui.notify(f'Project "{pid}" created with the sample pipeline.', type='positive')
            status_label.set_text(f'State: New project "{pid}"')
            return
        if action == 'delete':
            load_pipeline(notify=False)
            status_label.set_text(f'State: Switched to "{pid}"')
            return
        if default_storage.project_exists(pid):
            load_pipeline(notify=False)
            status_label.set_text(f'State: Switched to "{pid}"')
        else:
            nodes, edges = _sample_graph()
            flow.nodes = nodes
            flow.edges = edges
            status_label.set_text(f'State: "{pid}" has no saved pipeline yet')

    # --- Project bar -------------------------------------------------------
    with ui.row().classes('w-full items-center gap-4 q-mb-md'):
        project_manager = ProjectManager(value='default', on_switch=handle_project_switch)
        ui.space()
        status_label = ui.label('State: Ready').classes('text-sm font-semibold text-blue-700')

    # --- Action toolbar ----------------------------------------------------
    with ui.row().classes('w-full gap-4 items-center q-mb-md'):
        ui.button('Execute Pipeline', on_click=lambda: run_pipeline()).props('color=primary icon=play_arrow')
        ui.button('Save Pipeline', on_click=lambda: save_pipeline()).props('color=positive icon=save')
        ui.button('Load Pipeline', on_click=lambda: load_pipeline()).props('color=info icon=folder_open')
        ui.button('Reset Pipeline', on_click=lambda: reset_pipeline()).props('color=secondary icon=refresh')

    # --- Node palette ------------------------------------------------------
    with ui.card().classes('w-full q-mb-md p-3'):
        ui.label('Add Node').classes('font-bold text-sm q-mb-xs')
        with ui.row().classes('gap-2 items-center'):
            for kind in NODE_KINDS:
                _, palette_label = palette_entry(kind)
                ui.button(palette_label, on_click=lambda k=kind: open_node_dialog(k)).props('flat dense size=sm outline')
        ui.label('Double-click a node on the canvas to edit or delete it. Drag from the node dot to connect nodes.').classes('text-xs text-gray-500 q-mt-xs')

    flow = FlowEditor(nodes=copy.deepcopy(sample_nodes), edges=copy.deepcopy(sample_edges)).style('height: 480px; width: 100%;')

    # --- Output preview ----------------------------------------------------
    with ui.card().classes('w-full q-mt-md p-4'):
        ui.label('Pipeline Execution & Output Preview').classes('font-bold text-lg q-mb-xs')
        log_container = ui.log(max_lines=20).classes('w-full h-32 bg-gray-900 text-green-400 font-mono text-xs q-mb-md')
        log_container.push('ETL Flow Editor initialized. Use the palette to add nodes.')
        table_container = ui.column().classes('w-full overflow-x-auto')

    # --- Node property editor logic ----------------------------------------
    # Functions are declared before the dialogs that wire them up, because they
    # are passed as callback arguments (evaluated at build time, not on click).
    confirmed = {'node_id': None}

    def confirm_node_deletion():
        node_id = confirmed['node_id']
        confirmed['node_id'] = None
        confirm_dialog.close()
        if node_id is None:
            return
        removed = next((node for node in flow.nodes if node.get('id') == node_id), None)
        flow.nodes = [node for node in flow.nodes if node.get('id') != node_id]
        flow.edges = [
            edge for edge in flow.edges
            if edge.get('source') != node_id and edge.get('target') != node_id
        ]
        if removed:
            log_container.push(f'[Node Deleted] {node_id} "{removed.get("label", "")}"')
        status_label.set_text('State: Pipeline modified, save to persist')
        node_dialog.close()

    # --- Node form rendering ----------------------------------------------
    def render_node_form(kind, values):
        rendering['form'] = True
        try:
            node_field_inputs.clear()
            node_form_container.clear()
            with node_form_container:
                for field in fields_for(kind):
                    key = field['key']
                    current = values.get(key, field.get('default', ''))
                    if field['kind'] == 'choice':
                        element = ui.select(field['options'], label=field['label'], value=current)
                    else:
                        element = ui.input(field['label'], value=current)
                    element.classes('w-full')
                    if field.get('help'):
                        element.tooltip(field['help'])
                    node_field_inputs[key] = element
        finally:
            rendering['form'] = False

    def on_node_kind_changed(e):
        if rendering['form']:
            return
        kind = e.value or 'DataSource'
        if editing['node_id'] is None:
            node_title.text = f"New {NODE_KINDS[kind]['label']} node"
            node_save_button.text = 'Add Node'
        render_node_form(kind, default_values(kind))

    def open_node_dialog(kind, node_id=None):
        editing['node_id'] = node_id
        if node_id is None:
            node_title.text = f"New {NODE_KINDS[kind]['label']} node"
            node_save_button.text = 'Add Node'
            node_delete_button.set_enabled(False)
            render_node_form(kind, default_values(kind))
        else:
            node = flow.find_node(node_id)
            if node is None:
                return
            node_title.text = f"Edit node {node_id}"
            node_save_button.text = 'Save Node'
            node_delete_button.set_enabled(True)
            render_node_form(kind, node_values(node))
        rendering['form'] = True
        try:
            node_kind_select.value = kind
        finally:
            rendering['form'] = False
        node_dialog.open()

    def collect_form_values():
        return {key: (element.value or '') for key, element in node_field_inputs.items()}

    def save_node():
        kind = node_kind_select.value or 'DataSource'
        try:
            data = build_node_data(kind, collect_form_values())
        except ValueError as error:
            ui.notify(str(error), type='negative')
            return

        node_id = editing['node_id']
        if node_id is None:
            new_id = new_node_id(kind, [node.get('id') for node in flow.nodes])
            node = build_node(
                kind,
                collect_form_values(),
                new_id,
                {'x': NEW_NODE_X, 'y': 100 + NEW_NODE_Y_STEP * len(flow.nodes)},
            )
            flow.nodes = flow.nodes + [node]
            log_container.push(f'[Node Added] {node["label"]}')
        else:
            index = next((i for i, node in enumerate(flow.nodes) if node.get('id') == node_id), None)
            if index is None:
                ui.notify(f'Node "{node_id}" is no longer in the pipeline.', type='warning')
                node_dialog.close()
                return
            node = build_node(kind, collect_form_values(), node_id, flow.nodes[index].get('position', {}))
            updated = list(flow.nodes)
            updated[index] = node
            flow.nodes = updated
            log_container.push(f'[Node Updated] {node["label"]}')

        status_label.set_text('State: Pipeline modified, save to persist')
        node_dialog.close()

    def delete_node():
        node_id = editing['node_id']
        if node_id is None:
            return
        confirmed['node_id'] = node_id
        confirm_message.text = f'Delete node "{node_id}" and its connections?'
        confirm_dialog.open()

    # --- Node property editor dialogs --------------------------------------
    with ui.dialog() as node_dialog, ui.card().classes('w-[420px] gap-2'):
        node_title = ui.label().classes('text-lg font-bold')
        node_kind_select = (
            ui.select(list(NODE_KINDS), label='Node type', on_change=on_node_kind_changed)
            .classes('w-full')
        )
        node_form_container = ui.column().classes('w-full gap-2')
        node_field_inputs = {}
        with ui.row().classes('w-full justify-end gap-2'):
            node_delete_button = ui.button('Delete Node', on_click=lambda: delete_node()).props('color=negative outline')
            ui.button('Cancel', on_click=node_dialog.close).props('flat')
            node_save_button = ui.button('Add Node', on_click=lambda: save_node()).props('color=primary')

    with ui.dialog() as confirm_dialog, ui.card().classes('w-96 gap-2'):
        confirm_message = ui.label().classes('text-sm')
        with ui.row().classes('w-full justify-end gap-2'):
            ui.button('Cancel', on_click=confirm_dialog.close).props('flat')
            ui.button('Confirm', on_click=confirm_node_deletion).props('color=negative')

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
        open_node_dialog(node_kind(node), node_id)

    def handle_node_drag_stop(e):
        node = e.args.get('node', {})
        pos = e.args.get('node', {}).get('position', {})
        log_container.push(f'[Node Moved] Node "{node.get("id", "unknown")}" stopped at x={pos.get("x")}, y={pos.get("y")}')

    def handle_connect(e):
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
