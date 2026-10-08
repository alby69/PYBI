"""Python wrapper for Excel-like Pivot Table Vue component."""

from typing import Any, Dict, List, Optional
from nicegui import ui


class PivotTable(ui.element, component='pivot_table.js'):
    """PivotTable wraps an interactive Excel-like pivot table Vue component."""

    def __init__(
        self,
        data: Optional[List[Dict[str, Any]]] = None,
        columns: Optional[List[str]] = None,
        rows: Optional[List[str]] = None,
        cols: Optional[List[str]] = None,
        vals: Optional[Any] = None,
        values: Optional[Any] = None,
        filters: Optional[List[str]] = None,
        filter_values: Optional[Dict[str, Any]] = None,
        aggregator_name: str = 'Sum',
        show_row_subtotals: bool = True,
        show_col_subtotals: bool = True,
        show_grand_totals: bool = True,
        empty_value_placeholder: str = '—',
        read_only: bool = False,
        server_pivot_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__()

        # Polyfill process.env for browser ESM compatibility
        ui.add_head_html('<script>window.process = window.process || { env: { NODE_ENV: "production" } };</script>')

        self._data = data or []
        self._columns = columns or []
        self._rows = rows or []
        self._cols = cols or []
        self._vals = values if values is not None else (vals or [])
        self._filters = filters or []
        self._filter_values = filter_values or {}
        self._aggregator_name = aggregator_name
        self._show_row_subtotals = show_row_subtotals
        self._show_col_subtotals = show_col_subtotals
        self._show_grand_totals = show_grand_totals
        self._empty_value_placeholder = empty_value_placeholder
        self._read_only = read_only
        self._server_pivot_data = server_pivot_data

        self._props['data'] = self._data
        self._props['columns'] = self._columns
        self._props['rows'] = self._rows
        self._props['cols'] = self._cols
        self._props['vals'] = self._vals
        self._props['values'] = self._vals
        self._props['filters'] = self._filters
        self._props['filterValues'] = self._filter_values
        self._props['aggregatorName'] = self._aggregator_name
        self._props['showRowSubtotals'] = self._show_row_subtotals
        self._props['showColSubtotals'] = self._show_col_subtotals
        self._props['showGrandTotals'] = self._show_grand_totals
        self._props['emptyValuePlaceholder'] = self._empty_value_placeholder
        self._props['readOnly'] = self._read_only
        self._props['serverPivotData'] = self._server_pivot_data

    def update_data(self, new_data: List[Dict[str, Any]], columns: Optional[List[str]] = None) -> None:
        """Update dataset array."""
        self._data = new_data
        self._props['data'] = new_data
        if columns is not None:
            self._columns = columns
            self._props['columns'] = columns
        elif new_data and isinstance(new_data[0], dict):
            self._columns = list(new_data[0].keys())
            self._props['columns'] = self._columns
        self.update()

    def get_config(self) -> Dict[str, Any]:
        """Return current pivot configuration."""
        config = {
            'rows': self._rows,
            'cols': self._cols,
            'vals': self._vals,
            'aggregator_name': self._aggregator_name,
        }
        if self._filters:
            config['filters'] = self._filters
        if self._filter_values:
            config['filter_values'] = self._filter_values
        if not self._show_row_subtotals:
            config['show_row_subtotals'] = self._show_row_subtotals
        if not self._show_col_subtotals:
            config['show_col_subtotals'] = self._show_col_subtotals
        if not self._show_grand_totals:
            config['show_grand_totals'] = self._show_grand_totals
        if self._empty_value_placeholder != '—':
            config['empty_value_placeholder'] = self._empty_value_placeholder
        return config

    def set_config(self, config: Dict[str, Any]) -> None:
        """Set pivot configuration parameters."""
        if 'rows' in config:
            self._rows = config['rows'] or []
            self._props['rows'] = self._rows
        if 'cols' in config:
            self._cols = config['cols'] or []
            self._props['cols'] = self._cols
        if 'values' in config or 'vals' in config:
            self._vals = config.get('values') or config.get('vals') or []
            self._props['vals'] = self._vals
            self._props['values'] = self._vals
        if 'filters' in config:
            self._filters = config['filters'] or []
            self._props['filters'] = self._filters
        if 'filter_values' in config or 'filterValues' in config:
            self._filter_values = config.get('filter_values') or config.get('filterValues') or {}
            self._props['filterValues'] = self._filter_values
        if 'aggregator_name' in config or 'aggregatorName' in config:
            self._aggregator_name = config.get('aggregator_name') or config.get('aggregatorName') or 'Sum'
            self._props['aggregatorName'] = self._aggregator_name
        if 'show_row_subtotals' in config or 'showRowSubtotals' in config:
            self._show_row_subtotals = config.get('show_row_subtotals', config.get('showRowSubtotals', True))
            self._props['showRowSubtotals'] = self._show_row_subtotals
        if 'show_col_subtotals' in config or 'showColSubtotals' in config:
            self._show_col_subtotals = config.get('show_col_subtotals', config.get('showColSubtotals', True))
            self._props['showColSubtotals'] = self._show_col_subtotals
        if 'show_grand_totals' in config or 'showGrandTotals' in config:
            self._show_grand_totals = config.get('show_grand_totals', config.get('showGrandTotals', True))
            self._props['showGrandTotals'] = self._show_grand_totals
        if 'empty_value_placeholder' in config or 'emptyValuePlaceholder' in config:
            self._empty_value_placeholder = config.get('empty_value_placeholder', config.get('emptyValuePlaceholder', '—'))
            self._props['emptyValuePlaceholder'] = self._empty_value_placeholder
        self.update()
