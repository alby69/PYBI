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
        vals: Optional[List[str]] = None,
        aggregator_name: str = 'Sum',
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
        self._vals = vals or []
        self._aggregator_name = aggregator_name
        self._read_only = read_only
        self._server_pivot_data = server_pivot_data

        self._props['data'] = self._data
        self._props['columns'] = self._columns
        self._props['rows'] = self._rows
        self._props['cols'] = self._cols
        self._props['vals'] = self._vals
        self._props['aggregatorName'] = self._aggregator_name
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
        return {
            'rows': self._rows,
            'cols': self._cols,
            'vals': self._vals,
            'aggregator_name': self._aggregator_name,
        }

    def set_config(self, config: Dict[str, Any]) -> None:
        """Set pivot configuration parameters."""
        if 'rows' in config:
            self._rows = config['rows'] or []
            self._props['rows'] = self._rows
        if 'cols' in config:
            self._cols = config['cols'] or []
            self._props['cols'] = self._cols
        if 'vals' in config:
            self._vals = config['vals'] or []
            self._props['vals'] = self._vals
        if 'aggregator_name' in config or 'aggregatorName' in config:
            self._aggregator_name = config.get('aggregator_name') or config.get('aggregatorName') or 'Sum'
            self._props['aggregatorName'] = self._aggregator_name
        self.update()
