"""Widget configurator drawer and status badge helpers for Dashboard Editor."""

from typing import Callable, Dict, Any, Optional, List

from nicegui import ui

from pybi.ui.components.widget_data import source_fields

WIDGET_GALLERY = [
    {'type': 'kpi', 'icon': 'trending_up', 'label': 'KPI Card', 'description': 'Single key metric'},
    {'type': 'chart', 'icon': 'bar_chart', 'label': 'Chart', 'description': 'Bar, Line, Pie ECharts'},
    {'type': 'table', 'icon': 'table_chart', 'label': 'Data Table', 'description': 'Tabular data display'},
    {'type': 'pivot', 'icon': 'pivot_table_chart', 'label': 'Pivot Table', 'description': 'Excel-like drag & drop pivot table'},
    {'type': 'map', 'icon': 'map', 'label': 'Geographic Map', 'description': 'Geospatial visualization'},
    {'type': 'gauge', 'icon': 'speed', 'label': 'Gauge', 'description': 'Radial gauge metric'},
    {'type': 'text', 'icon': 'text_fields', 'label': 'Text Block', 'description': 'Formatted text / markdown'},
    {'type': 'image', 'icon': 'image', 'label': 'Image', 'description': 'Static or dynamic image'},
]


def _as_list(value: Any) -> List[str]:
    """Normalise a comma-separated string or list into a list of field names."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        return [part.strip() for part in value.split(',') if part.strip()]
    return [str(value).strip()]


def _union(options: List[str], values: List[str]) -> List[str]:
    """Return options plus any current values that are not already listed."""
    merged = list(options)
    for value in values:
        if value and value not in merged:
            merged.append(value)
    return merged


class WidgetConfigurator:
    """Side drawer for creating and configuring dashboard widget options."""

    def __init__(self, on_save: Callable[[Dict[str, Any]], None], on_delete: Optional[Callable[[Dict[str, Any]], None]] = None):
        self.on_save = on_save
        self.on_delete = on_delete
        self.drawer = ui.right_drawer(value=False).classes('bg-gray-50 border-l border-gray-200 p-0')
        self.drawer.style('width: 440px; max-width: 95vw;')
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
        default_source = 'regional_sales' if 'regional_sales' in sources else sources[0]
        gallery = {g['type']: g for g in WIDGET_GALLERY}
        default_type = 'kpi'
        self.current_widget = {
            'title': gallery[default_type]['label'],
            'type': default_type,
            'source': default_source,
            'value': '0',
            'subtitle': 'New metric',
        }
        self._is_new = True
        self._render(available_sources)

    def _render(self, available_sources: Optional[List[str]] = None):
        sources = available_sources or ['regional_sales']
        self._sources = sources
        header = 'Add Widget' if self._is_new else f"Configure: {self.current_widget.get('title', 'Widget')}"
        w_type = self.current_widget.get('type', 'kpi')
        current_source = self.current_widget.get('source') or (sources[0] if sources else '')
        fields = source_fields(current_source)
        dimensions = fields.get('dimensions', [])
        measures = fields.get('measures', [])
        all_fields = _union(dimensions, measures)

        self.drawer.clear()
        with self.drawer:
            with ui.column().classes('w-full h-full overflow-y-auto p-4 gap-3'):
                with ui.row().classes('w-full items-center gap-2'):
                    ui.icon(next((g['icon'] for g in WIDGET_GALLERY if g['type'] == w_type), 'widgets')).classes('text-blue-600')
                    ui.label(header).classes('text-xl font-bold text-slate-800')

                ud = self.current_widget
                ud_dims = _as_list(ud.get('dimensions'))
                ud_meas = _as_list(ud.get('measures'))

                # --- General settings -------------------------------------------------
                with ui.card().classes('w-full p-3 gap-2 shadow-none border rounded-lg bg-white'):
                    ui.label('Widget').classes('text-xs font-bold uppercase text-slate-500 tracking-wide')
                    title_inp = ui.input('Widget Title', value=ud.get('title', '')).classes('w-full')
                    type_select = ui.select(
                        options=[g['type'] for g in WIDGET_GALLERY],
                        label='Widget Type',
                        value=w_type,
                    ).classes('w-full')
                    type_select.on_value_change(lambda args, t=title_inp: self._on_type_change(args.value, t.value))

                # --- Data source ------------------------------------------------------
                with ui.card().classes('w-full p-3 gap-2 shadow-none border rounded-lg bg-white'):
                    ui.label('Data').classes('text-xs font-bold uppercase text-slate-500 tracking-wide')
                    with ui.row().classes('w-full items-center gap-2'):
                        source_select = ui.select(
                            options=sources,
                            label='Data Source / Semantic Model',
                            value=current_source,
                        ).classes('flex-1')
                        source_select.on_value_change(
                            lambda args, t=title_inp: self._on_source_change(args.value, t.value)
                        )
                        ui.button(
                            icon='refresh',
                            on_click=lambda t=title_inp: self._on_source_change(source_select.value, t.value)
                        ).props('flat round dense color=primary').tooltip('Ricarica campi fonte dati')

                    if all_fields:
                        ui.label(
                            f'{len(dimensions)} dimension(s) · {len(measures)} measure(s) available'
                        ).classes('text-xs text-slate-500')
                    else:
                        with ui.row().classes('w-full bg-amber-50 text-amber-800 p-3 rounded-lg text-xs items-start gap-2 border border-amber-200 mt-1'):
                            ui.icon('warning', size='sm').classes('text-amber-600 mt-0.5')
                            ui.label(f"Nessun campo rilevato per la fonte '{current_source}'. Verifica che la pipeline ETL sia stata eseguita o seleziona un'altra fonte dati.").classes('flex-1')

                # --- Widget specific fields ------------------------------------------
                dims_select = None
                meas_select = None
                val_inp = sub_inp = chart_type_select = metric_select = value_field_select = None
                selected_columns_select = None
                pivot_rows_inp = pivot_cols_inp = pivot_vals_inp = pivot_agg_select = pivot_filters_inp = None
                pivot_target_select = None

                if w_type == 'kpi':
                    value_options = _union(measures, [str(ud.get('valueField'))] if ud.get('valueField') else [])
                    value_field_select = ui.select(
                        options=value_options or [''],
                        label='Value Field',
                        value=ud.get('valueField') or (value_options[0] if value_options else ''),
                        clearable=True,
                    ).classes('w-full')
                    with ui.row().classes('w-full gap-2'):
                        metric_select = ui.select(
                            options=['sum', 'avg', 'min', 'max', 'count'],
                            label='Metric',
                            value=ud.get('metric', 'sum'),
                        ).classes('flex-1')
                        sub_inp = ui.input('Subtitle', value=str(ud.get('subtitle', ''))).classes('flex-1')
                    val_inp = ui.input('Static Value (fallback)', value=str(ud.get('value', ''))).classes('w-full')

                elif w_type == 'chart':
                    dims_select = ui.select(
                        options=_union(dimensions, ud_dims),
                        label='Dimensions',
                        value=ud_dims,
                        multiple=True,
                        with_input=True,
                    ).classes('w-full')
                    dims_select.on_value_change(
                        lambda e: self.current_widget.update({'dimensions': _as_list(e.value)})
                    )
                    meas_select = ui.select(
                        options=_union(measures, ud_meas),
                        label='Measures',
                        value=ud_meas,
                        multiple=True,
                        with_input=True,
                    ).classes('w-full')
                    meas_select.on_value_change(
                        lambda e: self.current_widget.update({'measures': _as_list(e.value)})
                    )
                    ui.label(
                        '💡 Suggerimento: Se l\'elenco è vuoto, puoi digitare manualmente il nome esatto della colonna e premere Invio.'
                    ).classes('text-xs text-slate-500 -mt-1')
                    ui.label(
                        'Tip: select two dimensions to use the second one as series/legend, then pick a measure.'
                    ).classes('text-xs text-slate-500 -mt-1')
                    chart_type_select = ui.select(
                        options=['bar', 'line', 'pie'],
                        label='Chart Style',
                        value=ud.get('chartType', 'bar'),
                    ).classes('w-full')

                elif w_type == 'table':
                    current_cols = _as_list(ud.get('selectedColumns'))
                    selected_columns_select = ui.select(
                        options=_union(dimensions, current_cols),
                        label='Columns to display',
                        value=current_cols,
                        multiple=True,
                        with_input=True,
                    ).classes('w-full')
                    selected_columns_select.on_value_change(
                        lambda e: self.current_widget.update({'selectedColumns': _as_list(e.value)})
                    )
                    ui.label('Leave empty to show every column.').classes('text-xs text-slate-500 -mt-1')

                elif w_type == 'pivot':
                    rows_val = _as_list(ud.get('rows'))
                    cols_val = _as_list(ud.get('cols'))
                    filters_val = _as_list(ud.get('filters'))
                    vals_val = ud.get('values') or ud.get('vals') or []
                    if isinstance(vals_val, list):
                        vals_str = ", ".join(v.get('field', str(v)) if isinstance(v, dict) else str(v) for v in vals_val)
                    else:
                        vals_str = str(vals_val or '')
                    agg_val = ud.get('aggregator_name') or ud.get('aggregatorName') or 'Sum'

                    with ui.card().classes('w-full p-3 gap-2 shadow-none border rounded-lg bg-white'):
                        ui.label('Pivot fields').classes('text-xs font-bold uppercase text-slate-500 tracking-wide')

                        def _make_pivot_input(label: str, value: str):
                            with ui.row().classes('w-full items-center gap-1 no-wrap'):
                                inp = ui.input(label, value=value).classes('flex-1')
                                adder = ui.select(options=all_fields, label='', with_input=True).props('dense outlined').classes('w-28')
                                adder.on_value_change(
                                    lambda e, target=inp, sel=adder: self._append_to_input(target, sel, e.value)
                                )
                            return inp

                        pivot_filters_inp = _make_pivot_input('Report Filters Fields (comma-separated)', ", ".join(filters_val))
                        pivot_rows_inp = _make_pivot_input('Rows Fields (comma-separated)', ", ".join(rows_val))
                        pivot_cols_inp = _make_pivot_input('Columns Fields (comma-separated)', ", ".join(cols_val))
                        pivot_vals_inp = _make_pivot_input('Values Fields (comma-separated)', vals_str)
                        pivot_agg_select = ui.select(
                            options=['Sum', 'Count', 'Average', 'Min', 'Max'],
                            label='Default Aggregator',
                            value=agg_val,
                        ).classes('w-full')
                        pivot_target_select = ui.select(
                            options=['Rows', 'Columns', 'Values', 'Filters'],
                            label='Aggiungi campo a',
                            value='Rows',
                        ).classes('w-full')

                # --- Available fields helper -----------------------------------------
                def add_field(field: str, is_measure: bool = False) -> None:
                    if w_type == 'pivot':
                        targets = {
                            'Rows': pivot_rows_inp,
                            'Columns': pivot_cols_inp,
                            'Values': pivot_vals_inp,
                            'Filters': pivot_filters_inp,
                        }
                        target = targets.get(pivot_target_select.value if pivot_target_select else 'Rows')
                        if target is not None:
                            values = _as_list(target.value)
                            if field not in values:
                                values.append(field)
                                target.value = ", ".join(values)
                        return
                    if is_measure:
                        target = meas_select or value_field_select or selected_columns_select or dims_select
                    else:
                        target = dims_select or selected_columns_select
                    self._add_field(field, target)

                if all_fields and w_type in ('chart', 'kpi', 'table', 'pivot'):
                    with ui.expansion('Campi disponibili (clicca per aggiungere)', icon='view_column', value=True).classes('w-full bg-white border rounded-lg'):
                        with ui.column().classes('w-full gap-2 p-1'):
                            if dimensions:
                                ui.label('Dimensions').classes('text-xs font-semibold text-slate-600')
                                with ui.row().classes('gap-1 flex-wrap'):
                                    for field in dimensions:
                                        ui.chip(
                                            field,
                                            icon='add',
                                            color='blue-1',
                                            text_color='blue-9',
                                            on_click=lambda f=field: add_field(f, is_measure=False),
                                        ).props('dense')
                            if measures:
                                ui.label('Measures').classes('text-xs font-semibold text-slate-600')
                                with ui.row().classes('gap-1 flex-wrap'):
                                    for field in measures:
                                        ui.chip(
                                            field,
                                            icon='add',
                                            color='green-1',
                                            text_color='green-9',
                                            on_click=lambda f=field: add_field(f, is_measure=True),
                                        ).props('dense')

                # --- Actions ----------------------------------------------------------
                with ui.row().classes('w-full justify-between items-center mt-2 pt-3 border-t'):
                    if not self._is_new and self.on_delete is not None:
                        ui.button('Delete', on_click=self._confirm_delete).props('flat dense color=negative icon=delete')
                    else:
                        ui.space()
                    with ui.row().classes('gap-2'):
                        ui.button('Cancel', on_click=self.close).props('flat dense')
                        ui.button('Apply', on_click=lambda: self._apply(
                            title_inp.value,
                            type_select.value,
                            source_select.value,
                            dims_select.value if dims_select is not None else None,
                            meas_select.value if meas_select is not None else None,
                            val_inp.value if val_inp is not None else None,
                            sub_inp.value if sub_inp is not None else None,
                            chart_type_select.value if chart_type_select is not None else None,
                            metric_select.value if metric_select is not None else None,
                            pivot_rows_inp.value if pivot_rows_inp is not None else None,
                            pivot_cols_inp.value if pivot_cols_inp is not None else None,
                            pivot_vals_inp.value if pivot_vals_inp is not None else None,
                            pivot_agg_select.value if pivot_agg_select is not None else None,
                            pivot_filters_inp.value if pivot_filters_inp is not None else None,
                            value_field_select.value if value_field_select is not None else None,
                            selected_columns_select.value if selected_columns_select is not None else None,
                        )).props('color=primary dense icon=check')

        self.drawer.set_value(True)

    @staticmethod
    def _append_to_input(target: ui.input, adder: ui.select, field: Optional[str]) -> None:
        """Append a field to a comma-separated input and reset the picker."""
        if not field:
            return
        values = _as_list(target.value)
        if field not in values:
            values.append(field)
            target.value = ", ".join(values)
        adder.value = None

    @staticmethod
    def _add_field(field: str, target: Optional[ui.select]) -> None:
        """Add a field to a multiple select control."""
        if target is None:
            return
        current = _as_list(target.value)
        if field not in current:
            current.append(field)
        target.value = current

    def close(self):
        """Close configurator drawer."""
        self.drawer.set_value(False)

    def _on_type_change(self, new_type: str, title: str) -> None:
        """Re-render the drawer so type-specific inputs follow the selected type."""
        self.current_widget['title'] = title
        self.current_widget['type'] = new_type
        self._render(self._sources)

    def _on_source_change(self, new_source: str, title: str) -> None:
        """Re-render the drawer so field lists follow the selected data source."""
        self.current_widget['title'] = title
        self.current_widget['source'] = new_source
        self._render(self._sources)

    def _apply(
        self,
        title,
        w_type,
        source,
        dims_value,
        meas_value,
        kpi_val,
        kpi_sub,
        chart_style,
        metric,
        pivot_rows=None,
        pivot_cols=None,
        pivot_vals=None,
        pivot_agg=None,
        pivot_filters=None,
        value_field=None,
        selected_columns=None,
    ):
        self.current_widget['title'] = title
        self.current_widget['type'] = w_type
        self.current_widget['source'] = source
        self.current_widget['dimensions'] = _as_list(dims_value)
        self.current_widget['measures'] = _as_list(meas_value)

        if kpi_val is not None:
            self.current_widget['value'] = kpi_val
        if kpi_sub is not None:
            self.current_widget['subtitle'] = kpi_sub
        if chart_style is not None:
            self.current_widget['chartType'] = chart_style
        if metric is not None:
            self.current_widget['metric'] = metric
        if value_field is not None:
            self.current_widget['valueField'] = value_field
        if selected_columns is not None:
            self.current_widget['selectedColumns'] = _as_list(selected_columns)

        if w_type == 'pivot':
            if pivot_rows is not None:
                self.current_widget['rows'] = _as_list(pivot_rows)
            if pivot_cols is not None:
                self.current_widget['cols'] = _as_list(pivot_cols)
            if pivot_filters is not None:
                self.current_widget['filters'] = _as_list(pivot_filters)
            if pivot_vals is not None:
                parsed_vals = _as_list(pivot_vals)
                default_agg = pivot_agg or 'Sum'
                self.current_widget['vals'] = [{'field': f, 'agg': default_agg, 'showAs': 'None'} for f in parsed_vals]
                self.current_widget['values'] = self.current_widget['vals']
            if pivot_agg is not None:
                self.current_widget['aggregator_name'] = pivot_agg

        self.on_save(self.current_widget)
        self.close()

    def _confirm_delete(self):
        with ui.dialog() as dialog, ui.card().classes('p-4 gap-3'):
            ui.label('Conferma eliminazione').classes('text-lg font-bold text-slate-800')
            title = self.current_widget.get('title', 'senza titolo')
            ui.label(f'Sei sicuro di voler eliminare il widget "{title}"?').classes('text-sm text-slate-600')
            with ui.row().classes('w-full justify-end gap-2 mt-2'):
                ui.button('Annulla', on_click=dialog.close).props('flat dense')
                ui.button('Elimina', on_click=lambda: (dialog.close(), self._delete())).props('color=negative dense icon=delete')
        dialog.open()

    def _delete(self):
        widget_id = self.current_widget.get('i')
        widget_title = self.current_widget.get('title')
        if self.on_delete is not None and (widget_id is not None or widget_title is not None):
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
