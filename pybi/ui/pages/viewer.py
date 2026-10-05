"""Public Viewer page implementation for read-only published dashboards."""

from nicegui import ui
from pybi.ui.components.dashboard_grid import DashboardGrid

from pybi.ui.components.navigation import render_navigation_bar

def create_viewer_page():
    render_navigation_bar('🚀 Executive Sales Dashboard (Published)', current_page='/viewer')
    ui.label('Public read-only viewer mode for end-user consultation. Dragging and resizing are disabled.').classes('text-sm text-gray-500 q-mb-md')

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
