"""Public Viewer page implementation for read-only published dashboards."""

from nicegui import ui
from pybi.ui.components.dashboard_grid import DashboardGrid

def create_viewer_page():
    with ui.row().classes('w-full items-center justify-between border-b pb-3 q-mb-md'):
        with ui.column().classes('gap-0'):
            ui.label('🚀 Executive Sales Dashboard (Published)').classes('text-2xl font-bold text-gray-900')
            ui.label('Public read-only viewer mode for end-user consultation. Dragging and resizing are disabled.').classes('text-sm text-gray-500')

        with ui.row().classes('gap-2 items-center'):
            ui.chip('READ ONLY', color='positive', text_color='white', icon='lock').classes('font-bold text-xs')
            ui.button('Back to Home', on_click=lambda: ui.navigate.to('/')).props('flat color=primary icon=home')

    # Published dashboard layout configuration
    published_layout = [
        {
            'i': 'w1',
            'x': 0, 'y': 0, 'w': 4, 'h': 3,
            'title': '💰 Total ARR',
            'type': 'kpi',
            'value': '$1,240,000',
            'subtitle': '▲ +22.1% YoY Growth'
        },
        {
            'i': 'w2',
            'x': 4, 'y': 0, 'w': 8, 'h': 4,
            'title': '📊 Quarterly Revenue Distribution',
            'type': 'chart',
            'chartType': 'Q1-Q4 Revenue Breakdown'
        },
        {
            'i': 'w3',
            'x': 0, 'y': 3, 'w': 4, 'h': 4,
            'title': '🌍 Regional Performance Summary',
            'type': 'table'
        }
    ]

    # Instantiate DashboardGrid in read-only mode
    grid = DashboardGrid(
        layout=published_layout,
        is_draggable=False,
        is_resizable=False
    ).style('min-height: 520px; width: 100%;')
