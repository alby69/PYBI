"""Dashboard Editor page implementation using DashboardGrid and ChartWidget with DataBinder."""

import copy
import math

from nicegui import ui
import polars as pl
from pybi.core.storage import default_storage
from pybi.dashboard import default_binder
from pybi.core.history import HistoryManager
from pybi.ui.components.chart_widget import ChartWidget
from pybi.ui.components.dashboard_grid import DashboardGrid
from pybi.ui.components.project_manager import ProjectManager
from pybi.export.dashboard_exporter import render_export_dialog
from pybi.ui.components.search_bar import SearchBar
from pybi.ui.components.widget_configurator import WidgetConfigurator, render_data_status_badge
from pybi.ui.shortcuts import render_shortcuts_help_button
from pybi.ui.theme import default_theme


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
            'chartType': 'Sales distribution across regions',
            'source': 'regional_sales'
        },
        {
            'i': 'w3',
            'x': 0, 'y': 3, 'w': 4, 'h': 4,
            'title': '📋 Top Performing Regions',
            'type': 'table',
            'source': 'regional_sales'
        }
    ]

    MAX_TABLE_ROWS = 50
    MAX_CHART_POINTS = 60
    MAX_CHART_SERIES = 3
    WIDGET_DATA_KEYS = ('columns', 'rows', 'row_count', 'truncated', 'data_error', 'chart')

    def available_sources():
        """Registered data source names usable as widget bindings."""
        try:
            names = default_binder.list_sources()
        except Exception:
            names = []
        return names or ['regional_sales']

    def _cell(value):
        """Make a DataFrame value JSON serializable for the browser."""
        if value is None or isinstance(value, (int, float, bool)):
            return value
        return str(value)

    def _number(value):
        """Coerce a numeric cell to a JSON-safe float, or None when not plottable."""
        if isinstance(value, bool) or value is None:
            return None
        if isinstance(value, (int, float)):
            return value if math.isfinite(value) else None
        return None

    def _source_frame(item):
        """Fetch the widget's bound DataFrame, or return (None, error message)."""
        source = item.get('source')
        if not source:
            return None, 'No data source selected'
        try:
            return default_binder.get_source_data(source), None
        except KeyError:
            return None, f'Unknown source "{source}" - run the ETL pipeline first'
        except Exception as err:
            return None, f'Failed to load source "{source}": {err}'

    def _bind_table_data(item, df, error):
        if error is not None:
            item['columns'] = []
            item['data_error'] = error
            return item
        view = df.head(MAX_TABLE_ROWS)
        item['columns'] = [str(c) for c in view.columns]
        item['rows'] = [[_cell(v) for v in row] for row in view.rows()]
        item['row_count'] = df.height
        item['truncated'] = df.height > MAX_TABLE_ROWS
        return item

    def _bind_chart_data(item, df, error):
        kind = item.get('chartType')
        kind = kind if kind in ('bar', 'line', 'pie') else 'bar'
        chart = {'kind': kind, 'labels': [], 'series': [], 'max': 0}
        item['chart'] = chart
        if error is not None:
            chart['error'] = error
            return item
        view = df.head(MAX_CHART_POINTS)
        if view.is_empty():
            chart['error'] = 'Source is empty'
            return item
        numeric = [c for c in view.columns if view[c].dtype.is_numeric()]
        if not numeric:
            chart['error'] = f'Source has no numeric column to plot ({", ".join(view.columns)})'
            return item
        label_col = next((c for c in view.columns if c not in numeric), None)
        if label_col is not None:
            chart['labels'] = [str(v) for v in view[label_col].to_list()]
        else:
            chart['labels'] = [str(i) for i in range(view.height)]
        for name in numeric[:MAX_CHART_SERIES]:
            values = [_number(v) for v in view[name].to_list()]
            chart['series'].append({'name': name, 'values': values})
        plottable = [v for s in chart['series'] for v in s['values'] if v is not None]
        chart['max'] = max(plottable) if plottable else 0
        if chart['max'] <= 0:
            chart['max'] = 1
        if view.height > MAX_CHART_POINTS:
            chart['truncated'] = True
        return item

    def _bind_widget_data(widget):
        """Attach live data pulled from the widget's bound source."""
        item = {k: v for k, v in widget.items() if k not in WIDGET_DATA_KEYS}
        if item.get('type') not in ('table', 'chart'):
            return item
        df, error = _source_frame(item)
        if item['type'] == 'table':
            return _bind_table_data(item, df, error)
        return _bind_chart_data(item, df, error)

    def bind_widget_data(layout):
        """Return a copy of the layout with live data attached to every widget."""
        return [_bind_widget_data(item) for item in layout]

    def strip_widget_data(layout):
        """Return a copy of the layout without the live data (for storage/export)."""
        return [{k: v for k, v in item.items() if k not in WIDGET_DATA_KEYS} for item in layout]

    def handle_project_switch(pid, action):
        if action == 'delete':
            reset_layout()
            status_label.set_text(f'State: Switched to "{pid}"')
            return
        try:
            layout_data = default_storage.load_dashboard_layout(pid)
        except Exception:
            layout_data = None
        grid.layout = bind_widget_data(copy.deepcopy(sample_layout) if layout_data is None else layout_data)
        if layout_data is None:
            log_container.push(f'[Storage] "{pid}" has no saved layout yet - demo widgets shown.')
            status_label.set_text(f'State: "{pid}" has no saved layout yet (demo widgets shown)')
        else:
            log_container.push(f'[Storage] "{pid}" layout loaded ({len(layout_data)} widget(s)).')
            status_label.set_text(f'State: "{pid}" layout loaded ({len(layout_data)} widget(s))')

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

    with ui.row().classes('w-full items-center gap-4 q-mb-md'):
        project_manager = ProjectManager(value='default', on_switch=handle_project_switch)
        ui.space()
        render_data_status_badge('fresh')
        status_label = ui.label('State: Ready').classes('text-sm font-semibold text-blue-700')

    grid = DashboardGrid(layout=bind_widget_data(copy.deepcopy(sample_layout)), is_draggable=True, is_resizable=True).style('min-height: 400px; width: 100%;')

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
        default_storage.save_dashboard_layout(pid, strip_widget_data(grid.layout))
        log_container.push(f'[Storage] Saved Dashboard layout for project "{pid}".')
        status_label.set_text(f'State: Layout saved to "{pid}"')
        ui.notify(f'Layout saved for project "{pid}"', type='positive')
        project_manager.refresh()

    def load_layout():
        pid = project_manager.project_id
        try:
            layout_data = default_storage.load_dashboard_layout(pid)
            if layout_data is None:
                grid.layout = bind_widget_data(copy.deepcopy(sample_layout))
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

    def reset_layout():
        grid.layout = bind_widget_data(copy.deepcopy(sample_layout))
        log_container.push('[Reset] Layout restored to default configuration.')
        status_label.set_text('State: Layout reset completed')

    if default_storage.project_exists(project_manager.project_id):
        try:
            saved_layout = default_storage.load_dashboard_layout(project_manager.project_id)
        except Exception:
            saved_layout = None
        if saved_layout is None:
            log_container.push(f'[Storage] "{project_manager.project_id}" has no saved layout - demo widgets shown. Use "Add Widget" to build your dashboard.')
            status_label.set_text(f'State: "{project_manager.project_id}" has no saved layout yet')
        else:
            grid.layout = bind_widget_data(saved_layout)
            if saved_layout:
                log_container.push(f'[Storage] Layout for "{project_manager.project_id}" restored on open ({len(saved_layout)} widget(s)).')
                status_label.set_text(f'State: Layout loaded from "{project_manager.project_id}"')
            else:
                log_container.push(f'[Storage] "{project_manager.project_id}" has an empty dashboard - use "Add Widget" to add widgets.')
                status_label.set_text(f'State: "{project_manager.project_id}" dashboard is empty')
