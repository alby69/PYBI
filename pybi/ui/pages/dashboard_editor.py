"""Dashboard Editor page implementation using DashboardGrid and ChartWidget with DataBinder."""

import copy

from nicegui import ui
import polars as pl

from pybi.core.storage import default_storage
from pybi.dashboard import default_binder
from pybi.core.history import HistoryManager
from pybi.ui.components.chart_widget import ChartWidget
from pybi.ui.components.dashboard_grid import DashboardGrid
from pybi.ui.components.dashboard_manager import DashboardManager
from pybi.ui.components.project_manager import ProjectManager
from pybi.ui.components.navbar import render_navbar
from pybi.export.dashboard_exporter import render_export_dialog
from pybi.ui.components.search_bar import SearchBar
from pybi.ui.components.widget_configurator import WidgetConfigurator, render_data_status_badge
from pybi.ui.components.widget_data import (
    available_sources,
    bind_widget_data,
    sample_layout,
    strip_widget_data,
)
from pybi.ui.shortcuts import render_shortcuts_help_button
from pybi.ui.theme import default_theme


def create_dashboard_editor_page():
    render_navbar(active='/dashboard-editor')
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

    def reset_layout():
        grid.layout = bind_widget_data(sample_layout())
        log_container.push('[Reset] Layout restored to default configuration.')
        status_label.set_text('State: Layout reset completed')

    def load_current_dashboard(notify: bool = True):
        """Load the selected dashboard's saved layout, or demo widgets when none saved."""
        pid = project_manager.project_id
        dash_id = dashboard_manager.dashboard_id
        if not dash_id:
            grid.layout = bind_widget_data(sample_layout())
            if notify:
                log_container.push(f'[Storage] "{pid}" has no saved dashboard - demo widgets shown.')
                status_label.set_text(f'State: "{pid}" has no saved dashboard yet (demo widgets shown)')
            return
        try:
            layout_data = default_storage.load_dashboard(pid, dash_id)
        except Exception:
            layout_data = None
        if layout_data is None:
            grid.layout = bind_widget_data(sample_layout())
            if notify:
                log_container.push(f'[Storage] "{pid}" has no saved layout yet - demo widgets shown.')
                status_label.set_text(f'State: "{pid}" has no saved layout yet (demo widgets shown)')
        else:
            grid.layout = bind_widget_data(layout_data)
            if notify:
                log_container.push(f'[Storage] "{pid}" layout loaded ({len(layout_data)} widget(s)).')
                status_label.set_text(f'State: "{pid}" layout loaded ({len(layout_data)} widget(s))')

    def handle_project_switch(pid, action):
        if action == 'delete':
            dashboard_manager.set_project(pid, select_first=True)
            load_current_dashboard(notify=True)
            status_label.set_text(f'State: Switched to "{pid}"')
            return
        dashboard_manager.set_project(pid, select_first=True)
        load_current_dashboard(notify=True)
        status_label.set_text(f'State: Switched to "{pid}"')

    def handle_dashboard_select(info):
        dashboard_manager.select.value = info.get('dashboard_id')
        dashboard_manager.select.update()
        load_current_dashboard(notify=True)

    def handle_dashboards_changed(info):
        dashboard_manager.refresh()
        if info.get('dashboard_id'):
            dashboard_manager.select.value = info.get('dashboard_id')
            dashboard_manager.select.update()
        load_current_dashboard(notify=True)

    history = HistoryManager()

    def record_history():
        history.push_state(copy.deepcopy(grid.layout))

    def apply_undo():
        prev = history.undo()
        if prev:
            grid.layout = prev
            log_container.push('[Undo] Restored previous layout state.')
            status_label.set_text('State: Layout undo applied')

    def apply_redo():
        nxt = history.redo()
        if nxt:
            grid.layout = nxt
            log_container.push('[Redo] Restored next layout state.')
            status_label.set_text('State: Layout redo applied')

    with ui.row().classes('w-full items-center gap-4 q-mb-md q-mt-md'):
        project_manager = ProjectManager(value='default', on_switch=handle_project_switch)
        dashboard_manager = DashboardManager(
            project_id=project_manager.project_id,
            on_select=handle_dashboard_select,
            on_changed=handle_dashboards_changed,
        )
        ui.space()
        render_data_status_badge('fresh')
        status_label = ui.label('State: Ready').classes('text-sm font-semibold text-blue-700')

    grid = DashboardGrid(layout=bind_widget_data(sample_layout()), is_draggable=True, is_resizable=True).style('min-height: 400px; width: 100%;')

    def next_widget_id(layout):
        used = set()
        for item in layout:
            raw = str(item.get('i', ''))
            if raw.startswith('w') and raw[1:].isdigit():
                used.add(int(raw[1:]))
        n = 1
        while n in used:
            n += 1
        return f'w{n}'

    def on_widget_configured(updated_widget):
        record_history()
        layout = list(grid.layout)
        if updated_widget.get('i'):
            for idx, item in enumerate(layout):
                if item.get('i') == updated_widget.get('i'):
                    layout[idx] = updated_widget
                    break
            log_container.push(f"[Config] Updated widget {updated_widget.get('i')} ({updated_widget.get('title')})")
        else:
            widget = dict(updated_widget)
            widget['i'] = next_widget_id(layout)
            widget['x'] = 0
            widget['y'] = max((int(item.get('y', 0)) + int(item.get('h', 1))) for item in layout) if layout else 0
            widget['w'] = int(widget.get('w', 4))
            widget['h'] = int(widget.get('h', 3))
            layout.append(widget)
            log_container.push(f"[Config] Added widget {widget['i']} ({widget['title']}, {widget['type']})")
        grid.layout = bind_widget_data(layout)
        status_label.set_text(f'State: {len(layout)} widget(s) on canvas')

    def on_widget_deleted(widget):
        record_history()
        layout = [item for item in grid.layout if item.get('i') != widget.get('i')]
        grid.layout = bind_widget_data(layout)
        log_container.push(f"[Config] Deleted widget {widget.get('i')} ({widget.get('title')})")
        status_label.set_text(f'State: {len(layout)} widget(s) on canvas')

    configurator = WidgetConfigurator(on_save=on_widget_configured, on_delete=on_widget_deleted)

    def get_search_items():
        return [{'id': item.get('i'), 'title': item.get('title'), 'type': item.get('type')} for item in grid.layout]

    def on_search_select(item):
        found = next((w for w in grid.layout if w.get('i') == item.get('id')), None)
        if found:
            configurator.open_widget(found, available_sources=available_sources())

    search_bar = SearchBar(items_provider=get_search_items, on_select=on_search_select)

    def on_grid_edit(e):
        widget = (e.args or {}).get('widget')
        if widget:
            configurator.open_widget(widget, available_sources=available_sources())

    grid.on_edit_widget(on_grid_edit)

    with ui.row().classes('w-full gap-2 items-center q-mb-md'):
        ui.button('Add Widget', on_click=lambda: configurator.open_new_widget(available_sources=available_sources())).props('color=primary icon=add')
        ui.button('Save Layout', on_click=lambda: save_layout()).props('color=positive icon=save')
        ui.button('Load Layout', on_click=lambda: load_layout()).props('color=info icon=folder_open')
        ui.button('Reset Layout', on_click=lambda: reset_layout()).props('color=secondary icon=refresh')
        ui.button('Refresh Data Source', on_click=lambda: refresh_source_data()).props('color=primary icon=autorenew')
        render_export_dialog(project_manager.project_id, grid.layout)
        ui.separator().props('vertical')
        ui.button(icon='undo', on_click=apply_undo).props('flat dense').tooltip('Undo (Ctrl+Z)')
        ui.button(icon='redo', on_click=apply_redo).props('flat dense').tooltip('Redo (Ctrl+Y)')
        search_bar.render_button()
        render_shortcuts_help_button()
        default_theme.render_toggle_button()

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
        log_container.push('Dashboard Editor initialized - drag, resize widgets and use "Add Widget" to build your layout.')

    def handle_layout_updated(e):
        record_history()
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
        grid.layout = bind_widget_data(grid.layout)
        log_container.push('[Data Source] Updated "regional_sales" data source. Widgets refreshed.')
        status_label.set_text('State: Source data refreshed')

    def save_layout():
        pid = project_manager.project_id
        dash_id = dashboard_manager.dashboard_id
        if not dash_id:
            dash_id = 'dash_1'
        name = dashboard_manager._current_name() or dash_id
        default_storage.save_dashboard(pid, dash_id, name, strip_widget_data(grid.layout))
        dashboard_manager.refresh()
        if dashboard_manager.dashboard_id == dash_id:
            dashboard_manager.select.value = dash_id
            dashboard_manager.select.update()
        log_container.push(f'[Storage] Saved Dashboard layout for project "{pid}".')
        status_label.set_text(f'State: Layout saved to "{pid}"')
        ui.notify(f'Layout saved for project "{pid}"', type='positive')
        project_manager.refresh()

    def load_layout():
        pid = project_manager.project_id
        dash_id = dashboard_manager.dashboard_id
        if not dash_id:
            grid.layout = bind_widget_data(sample_layout())
            log_container.push(f'[Storage] No saved dashboard for "{pid}" - demo widgets shown.')
            status_label.set_text(f'State: "{pid}" has no saved dashboard yet')
            ui.notify(f'No saved dashboard for "{pid}" - demo widgets shown', type='warning')
            return
        try:
            layout_data = default_storage.load_dashboard(pid, dash_id)
            if layout_data is None:
                grid.layout = bind_widget_data(sample_layout())
                log_container.push(f'[Storage] No saved layout for "{pid}" - demo widgets shown.')
                status_label.set_text(f'State: "{pid}" has no saved layout yet')
                ui.notify(f'No saved layout for "{pid}" - demo widgets shown', type='warning')
            else:
                grid.layout = bind_widget_data(layout_data)
                log_container.push(f'[Storage] Loaded Dashboard layout for project "{pid}" ({len(layout_data)} widget(s)).')
                status_label.set_text(f'State: Layout loaded from "{pid}"')
                ui.notify(f'Layout loaded for project "{pid}"', type='positive')
        except Exception as e:
            log_container.push(f'[Storage Error] Could not load project "{pid}": {e}')
            ui.notify(f'Failed to load project: {e}', type='negative')

    if default_storage.project_exists(project_manager.project_id):
        dashboard_manager.set_project(project_manager.project_id, select_first=True)
        load_current_dashboard(notify=False)
    else:
        log_container.push(f'[Storage] "{project_manager.project_id}" has no saved dashboard - demo widgets shown. Use "Add Widget" to build your dashboard.')
        status_label.set_text(f'State: "{project_manager.project_id}" has no saved dashboard yet')