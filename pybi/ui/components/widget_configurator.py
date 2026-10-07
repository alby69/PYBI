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
    """Side drawer for creating and configuring dashboard widget options."""

    def __init__(self, on_save: Callable[[Dict[str, Any]], None], on_delete: Optional[Callable[[Dict[str, Any]], None]] = None):
        self.on_save = on_save
        self.on_delete = on_delete
        self.drawer = ui.right_drawer(value=False).classes('bg-gray-50 border-l border-gray-200 p-4')
        self.drawer.style('width: 380px;')
        self.current_widget: Dict[str, Any] = {}
        self._is_new = False
        self._sources: List[str] = ['regional_sales']

    def open_widget(self, widget: Dict[str, Any], available_sources: Optional[List[str]] = None):
        """Open configurator drawer to edit an existing widget item."""
        self.current_widget = dict(widget)
        self._is_new = False
        self._render(available_sources)

    def open_new_widget(self, available_sources: Optional[List[str]] = None):
        """Open configurator drawer to create a brand new widget item."""
        sources = available_sources or ['regional_sales']
        gallery = {g['type']: g for g in WIDGET_GALLERY}
        default_type = 'kpi'
        self.current_widget = {
            'title': gallery[default_type]['label'],
            'type': default_type,
            'source': sources[0],
            'value': '0',
            'subtitle': 'New metric',
        }
        self._is_new = True
        self._render(available_sources)

    def _render(self, available_sources: Optional[List[str]] = None):
        sources = available_sources or ['regional_sales']
        self._sources = sources
        header = 'Add Widget' if self._is_new else f"Configure: {self.current_widget.get('title', 'Widget')}"

        self.drawer.clear()
        with self.drawer:
            ui.label(header).classes('text-xl font-bold mb-4')

            title_inp = ui.input('Widget Title', value=self.current_widget.get('title', '')).classes('w-full mb-3')

            w_type = self.current_widget.get('type', 'kpi')
            type_select = ui.select(
                options=[g['type'] for g in WIDGET_GALLERY],
                label='Widget Type',
                value=w_type
            ).classes('w-full mb-3')
            type_select.on_value_change(lambda args, t=title_inp: self._on_type_change(args.value, t.value))

            source_select = ui.select(
                options=sources,
                label='Data Source',
                value=self.current_widget.get('source', sources[0] if sources else '')
            ).classes('w-full mb-3')

            val_inp = sub_inp = chart_type_select = metric_select = None
            if w_type == 'kpi':
                val_inp = ui.input('Value', value=str(self.current_widget.get('value', ''))).classes('w-full mb-2')
                sub_inp = ui.input('Subtitle', value=str(self.current_widget.get('subtitle', ''))).classes('w-full mb-2')
                metric_select = ui.select(
                    options=['sum', 'avg', 'min', 'max', 'count'],
                    label='Metric',
                    value=self.current_widget.get('metric', 'sum')
                ).classes('w-full mb-2')
            elif w_type == 'chart':
                chart_type_select = ui.select(
                    options=['bar', 'line', 'pie'],
                    label='Chart Style',
                    value=self.current_widget.get('chartType', 'bar')
                ).classes('w-full mb-2')

            with ui.row().classes('w-full justify-between items-center mt-6'):
                if not self._is_new and self.on_delete is not None:
                    ui.button('Delete', on_click=self._delete).props('flat dense color=negative icon=delete')
                else:
                    ui.space()
                ui.button('Cancel', on_click=self.close).props('flat dense')
                ui.button('Apply', on_click=lambda: self._apply(
                    title_inp.value,
                    type_select.value,
                    source_select.value,
                    val_inp.value if val_inp is not None else None,
                    sub_inp.value if sub_inp is not None else None,
                    chart_type_select.value if chart_type_select is not None else None,
                    metric_select.value if metric_select is not None else None
                )).props('color=primary dense')

        self.drawer.set_value(True)

    def close(self):
        """Close configurator drawer."""
        self.drawer.set_value(False)

    def _on_type_change(self, new_type: str, title: str) -> None:
        """Re-render the drawer so type-specific inputs follow the selected type."""
        self.current_widget['title'] = title
        self.current_widget['type'] = new_type
        self._render(self._sources)

    def _apply(self, title, w_type, source, kpi_val, kpi_sub, chart_style, metric):
        self.current_widget['title'] = title
        self.current_widget['type'] = w_type
        self.current_widget['source'] = source
        if kpi_val is not None:
            self.current_widget['value'] = kpi_val
        if kpi_sub is not None:
            self.current_widget['subtitle'] = kpi_sub
        if chart_style is not None:
            self.current_widget['chartType'] = chart_style
        if metric is not None:
            self.current_widget['metric'] = metric

        self.on_save(self.current_widget)
        self.close()

    def _delete(self):
        widget_id = self.current_widget.get('i')
        if self.on_delete is not None and widget_id is not None:
            self.on_delete(dict(self.current_widget))
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
