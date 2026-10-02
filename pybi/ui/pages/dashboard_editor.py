"""Dashboard Editor page implementation using DashboardGrid and ChartWidget with DataBinder."""

import copy

from nicegui import ui
import polars as pl
from pybi.core.storage import default_storage
from pybi.dashboard import default_binder
from pybi.ui.components.chart_widget import ChartWidget
from pybi.ui.components.dashboard_grid import DashboardGrid
from pybi.ui.components.project_manager import ProjectManager


def create_dashboard_editor_page():
    ui.label('Dashboard Editor - Canvas & Chart Binding').classes('text-2xl font-bold q-mb-sm')
    ui.label('Interactive dashboard layout builder using Vue Grid Layout with live DataBinder chart widgets.').classes('text-gray-600 q-mb-md')

    # Register initial sample data source if not registered
    try:
        default_binder.get_source_data('regional_sales')
    except KeyError:
        sample_df = pl.DataFrame({
            'region': ['Europe', 'North America', 'Asia Pacific', 'Latin America'],
            'revenue': [1200, 1850, 950, 420],
            'units_sold': [120, 190, 85, 45]
        })
        default_binder.register_source('regional_sales', sample_df)

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

    def handle_project_switch(pid, action):
        if action == 'delete':
            reset_layout()
            status_label.set_text(f'State: Switched to "{pid}"')
            return
        try:
            layout_data = default_storage.load_dashboard_layout(pid)
        except Exception:
            layout_data = []
        grid.layout = layout_data if layout_data else copy.deepcopy(sample_layout)
        status_label.set_text(f'State: "{pid}" layout loaded' if layout_data else f'State: "{pid}" has no saved layout yet')

    with ui.row().classes('w-full items-center gap-4 q-mb-md'):
        project_manager = ProjectManager(value='default', on_switch=handle_project_switch)
        ui.space()
        status_label = ui.label('State: Ready').classes('text-sm font-semibold text-blue-700')

    grid = DashboardGrid(layout=sample_layout, is_draggable=True, is_resizable=True).style('min-height: 400px; width: 100%;')

    with ui.row().classes('w-full gap-4 items-center q-mb-md'):
        ui.button('Save Layout', on_click=lambda: save_layout()).props('color=positive icon=save')
        ui.button('Load Layout', on_click=lambda: load_layout()).props('color=info icon=folder_open')
        ui.button('Reset Layout', on_click=lambda: reset_layout()).props('color=secondary icon=refresh')
        ui.button('Refresh Data Source', on_click=lambda: refresh_source_data()).props('color=primary icon=autorenew')

    # Dynamic Chart Widget bound to DataBinder
    with ui.card().classes('w-full q-mt-md p-4'):
        chart_container = ui.column().classes('w-full')

        with chart_container:
            chart = ChartWidget(
                chart_type='bar',
                x_col='region',
                y_cols=['revenue'],
                title='Regional Sales Revenue'
            )
            chart.bind_to(
                binder=default_binder,
                widget_id='w2_chart',
                source_name='regional_sales',
                x_col='region',
                y_cols=['revenue']
            )

            with ui.row().classes('w-full items-center justify-between q-mt-xs'):
                ui.label('Dynamic Data-Bound Chart Widget').classes('font-bold text-sm text-gray-700')
                with ui.row().classes('gap-2'):
                    ui.button('Bar Chart', on_click=lambda: chart.update_data(chart._df, chart_type='bar')).props('outline dense size=sm color=primary')
                    ui.button('Line Chart', on_click=lambda: chart.update_data(chart._df, chart_type='line')).props('outline dense size=sm color=primary')
                    ui.button('Pie Chart', on_click=lambda: chart.update_data(chart._df, chart_type='pie')).props('outline dense size=sm color=primary')

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

    def refresh_source_data():
        updated_df = pl.DataFrame({
            'region': ['Europe', 'North America', 'Asia Pacific', 'Latin America'],
            'revenue': [1500, 2100, 1300, 680],
            'units_sold': [150, 210, 110, 60]
        })
        default_binder.update_source('regional_sales', updated_df)
        log_container.push('[Data Source] Updated "regional_sales" data source. Chart refreshed reactively.')
        status_label.set_text('State: Source data refreshed')

    def save_layout():
        pid = project_manager.project_id
        default_storage.save_dashboard_layout(pid, grid.layout)
        log_container.push(f'[Storage] Saved Dashboard layout for project "{pid}".')
        status_label.set_text(f'State: Layout saved to "{pid}"')
        ui.notify(f'Layout saved for project "{pid}"', type='positive')
        project_manager.refresh()

    def load_layout():
        pid = project_manager.project_id
        try:
            layout_data = default_storage.load_dashboard_layout(pid)
            if layout_data:
                grid.layout = layout_data
            log_container.push(f'[Storage] Loaded Dashboard layout for project "{pid}".')
            status_label.set_text(f'State: Layout loaded from "{pid}"')
            ui.notify(f'Layout loaded for project "{pid}"', type='positive')
        except Exception as e:
            log_container.push(f'[Storage Error] Could not load project "{pid}": {e}')
            ui.notify(f'Failed to load project: {e}', type='negative')

    def reset_layout():
        grid.layout = copy.deepcopy(sample_layout)
        log_container.push('[Reset] Layout restored to default configuration.')
        status_label.set_text('State: Layout reset completed')

    if default_storage.project_exists(project_manager.project_id):
        try:
            saved_layout = default_storage.load_dashboard_layout(project_manager.project_id)
        except Exception:
            saved_layout = []
        if saved_layout:
            grid.layout = saved_layout
            log_container.push(f'[Storage] Layout for "{project_manager.project_id}" restored on open.')
            status_label.set_text(f'State: Layout loaded from "{project_manager.project_id}"')
