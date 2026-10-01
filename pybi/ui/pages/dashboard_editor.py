"""Dashboard Editor page implementation using DashboardGrid component."""

from nicegui import ui
from pybi.ui.components.dashboard_grid import DashboardGrid

def create_dashboard_editor_page():
    ui.label('Dashboard Editor - Drag & Drop Canvas').classes('text-2xl font-bold q-mb-sm')
    ui.label('Interactive dashboard layout builder using Vue Grid Layout. Drag widgets by header or resize using bottom-right handle.').classes('text-gray-600 q-mb-md')

    # Initial sample dashboard widgets layout
    sample_layout = [
        {
            'i': 'w1',
            'x': 0, 'y': 0, 'w': 4, 'h': 3,
            'title': '📊 Quarterly Revenue',
            'type': 'kpi',
            'value': '$248,900',
            'subtitle': '▲ +18.4% vs Q2'
        },
        {
            'i': 'w2',
            'x': 4, 'y': 0, 'w': 8, 'h': 4,
            'title': '📈 Regional Sales Bar Chart',
            'type': 'chart',
            'chartType': 'Sales distribution across regions'
        },
        {
            'i': 'w3',
            'x': 0, 'y': 3, 'w': 4, 'h': 4,
            'title': '📋 Top Performing Regions',
            'type': 'table'
        }
    ]

    with ui.row().classes('w-full gap-4 items-center q-mb-md'):
        ui.button('Reset Layout', on_click=lambda: reset_layout()).props('color=secondary icon=refresh')
        status_label = ui.label('State: Ready').classes('text-sm font-semibold text-blue-700')

    grid = DashboardGrid(layout=sample_layout, is_draggable=True, is_resizable=True).style('min-height: 500px; width: 100%;')

    with ui.card().classes('w-full q-mt-md p-4'):
        ui.label('Live Event & Layout State Log').classes('font-bold text-lg q-mb-xs')
        log_container = ui.log(max_lines=20).classes('w-full h-32 bg-gray-900 text-blue-400 font-mono text-xs')
        log_container.push('Dashboard Editor initialized with 3 resizable/draggable widgets.')

    def handle_layout_updated(e):
        layout = e.args.get('layout', [])
        summary = ", ".join([f"{item.get('i')}:({item.get('x')},{item.get('y')},{item.get('w')}x{item.get('h')})" for item in layout])
        log_container.push(f'[Layout Updated] {summary}')
        status_label.set_text(f'State: Layout updated ({len(layout)} items)')

    grid.on_layout_updated(handle_layout_updated)

    def reset_layout():
        grid.layout = sample_layout
        log_container.push('[Reset] Layout restored to default configuration.')
        status_label.set_text('State: Layout reset completed')
