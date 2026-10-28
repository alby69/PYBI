"""Python wrapper for Report Tablix Vue component."""

from typing import Any, Dict, List, Optional
from nicegui import ui


class ReportTablix(ui.element, component='report_tablix.js'):
    """ReportTablix wraps hierarchical multi-level row grouping with conditional formatting."""

    def __init__(
        self,
        data: Optional[List[Dict[str, Any]]] = None,
        columns: Optional[List[str]] = None,
        row_groups: Optional[List[str]] = None,
        measures: Optional[List[Dict[str, Any]]] = None,
        conditional_formatting: Optional[List[Dict[str, Any]]] = None,
        drill_action: Optional[Dict[str, Any]] = None,
        show_grand_total: bool = True,
    ) -> None:
        super().__init__()

        # Polyfill process.env for browser ESM compatibility
        ui.add_head_html('<script>window.process = window.process || { env: { NODE_ENV: "production" } };</script>')

        self._data = data or []
        self._columns = columns or []
        self._row_groups = row_groups or []
        self._measures = measures or []
        self._conditional_formatting = conditional_formatting or []
        self._drill_action = drill_action
        self._show_grand_total = show_grand_total

        self._props['data'] = self._data
        self._props['columns'] = self._columns
        self._props['rowGroups'] = self._row_groups
        self._props['measures'] = self._measures
        self._props['conditionalFormatting'] = self._conditional_formatting
        self._props['drillAction'] = self._drill_action
        self._props['showGrandTotal'] = self._show_grand_total

    def update_data(self, new_data: List[Dict[str, Any]], columns: Optional[List[str]] = None) -> None:
        """Update dataset array and columns."""
        self._data = new_data
        self._props['data'] = new_data
        if columns is not None:
            self._columns = columns
            self._props['columns'] = columns
        elif new_data and isinstance(new_data[0], dict):
            self._columns = list(new_data[0].keys())
            self._props['columns'] = self._columns
        self.update()
