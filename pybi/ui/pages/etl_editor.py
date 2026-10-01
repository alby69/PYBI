"""ETL Editor page implementation with FlowEditor component."""

from nicegui import ui
from pybi.ui.components.flow_editor import FlowEditor

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
            'style': {'background': '#e0f2fe', 'border': '2px solid #0284c7', 'borderRadius': '8px', 'padding': '10px'}
        },
        {
            'id': 'node_2',
            'label': '⚡ Filter Rows (region == "EU")',
            'position': {'x': 320, 'y': 100},
            'style': {'background': '#fef3c7', 'border': '2px solid #d97706', 'borderRadius': '8px', 'padding': '10px'}
        },
        {
            'id': 'node_3',
            'type': 'output',
            'label': '💾 DuckDB Table (filtered_sales)',
            'position': {'x': 600, 'y': 100},
            'style': {'background': '#dcfce7', 'border': '2px solid #16a34a', 'borderRadius': '8px', 'padding': '10px'}
        }
    ]

    # Initial sample connections
    sample_edges = [
        {'id': 'e1-2', 'source': 'node_1', 'target': 'node_2', 'label': 'raw_stream'},
        {'id': 'e2-3', 'source': 'node_2', 'target': 'node_3', 'label': 'filtered_stream'}
    ]

    with ui.row().classes('w-full gap-4 items-center q-mb-md'):
        ui.button('Reset Pipeline', on_click=lambda: reset_pipeline()).props('color=secondary icon=refresh')
        status_label = ui.label('State: Ready').classes('text-sm font-semibold text-blue-700')

    flow = FlowEditor(nodes=sample_nodes, edges=sample_edges).style('height: 520px; width: 100%;')

    with ui.card().classes('w-full q-mt-md p-4'):
        ui.label('Live Event & State Log').classes('font-bold text-lg q-mb-xs')
        log_container = ui.log(max_lines=20).classes('w-full h-32 bg-gray-900 text-green-400 font-mono text-xs')
        log_container.push('ETL Flow Editor initialized with 3 nodes and 2 edges.')

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

    def reset_pipeline():
        flow.nodes = sample_nodes
        flow.edges = sample_edges
        log_container.push('[Reset] Pipeline restored to initial state.')
        status_label.set_text('State: Reset completed')
