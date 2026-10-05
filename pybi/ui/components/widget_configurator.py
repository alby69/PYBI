"""Widget configurator drawer and status badge helpers for Dashboard Editor."""

from typing import Callable, Dict, Any, Optional, List
from nicegui import ui

WIDGET_GALLERY = [
    {'type': 'kpi', 'icon': 'trending_up', 'label': 'KPI Card', 'description': 'Single key metric'},
    {'type': 'chart', 'icon': 'bar_chart', 'label': 'Chart', 'description': 'Bar, Line, Pie ECharts'},
    {'type': 'table', 'icon': 'table_chart', 'label': 'Data Table', 'description': 'Tabular data display'},
    {'type': 'map', 'icon': 'map', 'label': 'Geographic Map', 'description': 'Geospatial visualization'},
    {'type': 'gauge', 'icon': 'speed', 'label': 'Gauge', 'description': 'Radial gauge metric'},
    {'type': 'text', 'icon': 'text_fields', 'label': 'Text Block', 'description': 'Formatted text / markdown'},
    {'type': 'image', 'icon': 'image', 'label': 'Image', 'description': 'Static or dynamic image'},
]


class WidgetConfigurator:
    """Side drawer for configuring dashboard widget options."""

    def __init__(self, on_save: Callable[[Dict[str, Any]], None]):
        self.on_save = on_save
        self.drawer = ui.right_drawer(value=False).classes('bg-gray-50 border-l border-gray-200 p-4')
        self.drawer.style('width: 380px;')
        self.current_widget: Dict[str, Any] = {}

    def open_widget(self, widget: Dict[str, Any], available_sources: Optional[List[str]] = None):
        """Open configurator drawer for a specific widget item."""
        self.current_widget = dict(widget)
        sources = available_sources or ['regional_sales']

        self.drawer.clear()
        with self.drawer:
            ui.label(f"Configure: {self.current_widget.get('title', 'Widget')}").classes('text-xl font-bold mb-4')

            title_inp = ui.input('Widget Title', value=self.current_widget.get('title', '')).classes('w-full mb-3')

            w_type = self.current_widget.get('type', 'kpi')
            type_select = ui.select(
                options=[g['type'] for g in WIDGET_GALLERY],
                label='Widget Type',
                value=w_type
            ).classes('w-full mb-3')

            source_select = ui.select(
                options=sources,
                label='Data Source',
                value=self.current_widget.get('source', sources[0] if sources else '')
            ).classes('w-full mb-3')

            if w_type == 'kpi':
                val_inp = ui.input('Value', value=str(self.current_widget.get('value', ''))).classes('w-full mb-2')
                sub_inp = ui.input('Subtitle', value=str(self.current_widget.get('subtitle', ''))).classes('w-full mb-2')
            elif w_type == 'chart':
                chart_type_select = ui.select(
                    options=['bar', 'line', 'pie'],
                    label='Chart Style',
                    value=self.current_widget.get('chartType', 'bar')
                ).classes('w-full mb-2')

            with ui.row().classes('w-full justify-end gap-2 mt-6'):
                ui.button('Cancel', on_click=self.close).props('flat dense')
                ui.button('Apply', on_click=lambda: self._apply(
                    title_inp.value,
                    type_select.value,
                    source_select.value,
                    val_inp.value if w_type == 'kpi' else None,
                    sub_inp.value if w_type == 'kpi' else None,
                    chart_type_select.value if w_type == 'chart' else None
                )).props('color=primary dense')

        self.drawer.set_value(True)

    def close(self):
        """Close configurator drawer."""
        self.drawer.set_value(False)

    def _apply(self, title, w_type, source, kpi_val, kpi_sub, chart_style):
        self.current_widget['title'] = title
        self.current_widget['type'] = w_type
        self.current_widget['source'] = source
        if kpi_val is not None:
            self.current_widget['value'] = kpi_val
        if kpi_sub is not None:
            self.current_widget['subtitle'] = kpi_sub
        if chart_style is not None:
            self.current_widget['chartType'] = chart_style

        self.on_save(self.current_widget)
        self.close()


def render_data_status_badge(status: str = 'fresh'):
    """Render a data status badge indicator."""
    badge_colors = {
        'fresh': 'green',
        'stale': 'amber',
        'error': 'red',
        'loading': 'blue'
    }
    color = badge_colors.get(status, 'gray')
    badge = ui.badge(status.title(), color=color).props('floating')
    return badge
