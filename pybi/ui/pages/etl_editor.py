"""ETL Editor page implementation with FlowEditor component and ETLExecutor."""

from nicegui import ui
from pybi.core.storage import default_storage
from pybi.etl.executor import execute_dag
from pybi.ui.components.flow_editor import FlowEditor
from pybi.dashboard.binding import default_binder


def create_etl_editor_page():
    ui.label('ETL Editor - Pipeline DAG Builder').classes('text-2xl font-bold q-mb-sm')
    ui.label('Visual ETL pipeline editor using Vue Flow integration. Drag nodes or connect ports to modify pipeline graph.').classes('text-gray-600 q-mb-md')

    # Initial sample ETL nodes
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

    # Initial sample connections
    sample_edges = [
        {'id': 'e1-2', 'source': 'node_1', 'target': 'node_2', 'label': 'raw_stream'},
        {'id': 'e2-3', 'source': 'node_2', 'target': 'node_3', 'label': 'filtered_stream'}
    ]

    project_input = ui.input('Project ID', value='default').classes('w-32')

    with ui.row().classes('w-full gap-4 items-center q-mb-md'):
        ui.button('Execute Pipeline', on_click=lambda: run_pipeline()).props('color=primary icon=play_arrow')
        ui.button('Save Pipeline', on_click=lambda: save_pipeline()).props('color=positive icon=save')
        ui.button('Load Pipeline', on_click=lambda: load_pipeline()).props('color=info icon=folder_open')
        ui.button('Reset Pipeline', on_click=lambda: reset_pipeline()).props('color=secondary icon=refresh')
        status_label = ui.label('State: Ready').classes('text-sm font-semibold text-blue-700')

    flow = FlowEditor(nodes=sample_nodes, edges=sample_edges).style('height: 480px; width: 100%;')

    # Output preview section
    with ui.card().classes('w-full q-mt-md p-4'):
        ui.label('Pipeline Execution & Output Preview').classes('font-bold text-lg q-mb-xs')
        log_container = ui.log(max_lines=20).classes('w-full h-32 bg-gray-900 text-green-400 font-mono text-xs q-mb-md')
        log_container.push('ETL Flow Editor initialized with 3 nodes and 2 edges.')

        table_container = ui.column().classes('w-full overflow-x-auto')

    def handle_node_drag(e):
        node_id = e.args.get('node', {}).get('id', 'unknown')
        pos = e.args.get('node', {}).get('position', {})
        log_container.push(f'[Node Moved] Node "{node_id}" stopped at x={pos.get("x")}, y={pos.get("y")}')
        status_label.set_text(f'State: Node {node_id} repositioned')

    def handle_connect(e):
        conn = e.args.get('connection', {})
        log_container.push(f'[Connection Created] Connected {conn.get("source")} -> {conn.get("target")}')
        status_label.set_text(f'State: New connection {conn.get("source")} -> {conn.get("target")}')

    def handle_change(e):
        nodes_count = len(e.args.get('nodes', []))
        edges_count = len(e.args.get('edges', []))
        log_container.push(f'[State Updated] Nodes count: {nodes_count}, Edges count: {edges_count}')

    flow.on_node_drag_stop(handle_node_drag)
    flow.on_connect(handle_connect)
    flow.on_change(handle_change)

    def run_pipeline():
        log_container.push('[Execution] Starting DAG execution engine...')
        status_label.set_text('State: Executing DAG...')

        dag_data = {'nodes': flow.nodes, 'edges': flow.edges}
        result = execute_dag(dag_data, duckdb_conn=default_binder.duckdb_conn)

        for log in result.logs:
            log_container.push(f'[Engine Log] {log}')

        if result.status == 'success':
            status_label.set_text('State: Execution Succeeded')
            table_container.clear()
            with table_container:
                if result.output_tables:
                    for tbl_name, df in result.output_tables.items():
                        # Register in default_binder for dashboard access
                        default_binder.register_source(tbl_name, df)
                        ui.label(f'Output Table: {tbl_name} ({len(df)} rows)').classes('font-semibold text-sm text-gray-800 q-mb-xs')
                        columns = [{'name': c, 'label': c, 'field': c, 'sortable': True} for c in df.columns]
                        rows = df.to_dicts()
                        ui.table(columns=columns, rows=rows, row_key='id').classes('w-full')
                elif result.dataframes:
                    last_node_id = list(result.dataframes.keys())[-1]
                    df = result.dataframes[last_node_id]
                    ui.label(f'Node Output: {last_node_id} ({len(df)} rows)').classes('font-semibold text-sm text-gray-800 q-mb-xs')
                    columns = [{'name': c, 'label': c, 'field': c, 'sortable': True} for c in df.columns]
                    rows = df.to_dicts()
                    ui.table(columns=columns, rows=rows, row_key='id').classes('w-full')
        else:
            status_label.set_text(f'State: Execution Failed ({result.error})')
            ui.notify(f'Execution Error: {result.error}', type='negative')

    def save_pipeline():
        pid = project_input.value or 'default'
        dag_data = {'nodes': flow.nodes, 'edges': flow.edges}
        default_storage.save_etl_dag(pid, dag_data)
        log_container.push(f'[Storage] Saved ETL DAG for project "{pid}".')
        status_label.set_text(f'State: Pipeline saved to "{pid}"')
        ui.notify(f'Pipeline saved for project "{pid}"', type='positive')

    def load_pipeline():
        pid = project_input.value or 'default'
        try:
            dag_data = default_storage.load_etl_dag(pid)
            flow.nodes = dag_data.get('nodes', [])
            flow.edges = dag_data.get('edges', [])
            log_container.push(f'[Storage] Loaded ETL DAG for project "{pid}".')
            status_label.set_text(f'State: Pipeline loaded from "{pid}"')
            ui.notify(f'Pipeline loaded for project "{pid}"', type='positive')
        except Exception as e:
            log_container.push(f'[Storage Error] Could not load project "{pid}": {e}')
            ui.notify(f'Failed to load project: {e}', type='negative')

    def reset_pipeline():
        flow.nodes = sample_nodes
        flow.edges = sample_edges
        table_container.clear()
        log_container.push('[Reset] Pipeline restored to initial state.')
        status_label.set_text('State: Reset completed')
