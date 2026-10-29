"""Python wrapper component for Power Query Editor Vue 3 interface."""

from typing import Any, Dict, List, Optional
from nicegui import ui


class PowerQueryEditor(ui.element, component='PowerQueryEditor.vue'):
    """NiceGUI element wrapping the 5-panel Power Query Editor Vue 3 component."""

    def __init__(
        self,
        tables: Optional[List[str]] = None,
        selected_table: Optional[str] = None,
        applied_steps_by_table: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ) -> None:
        super().__init__()

        # Polyfill window.process for browser ESM compatibility
        ui.add_head_html('<script>window.process = window.process || { env: { NODE_ENV: "production" } };</script>')

        self._tables = tables or ["sales_data.csv"]
        self._selected_table = selected_table or self._tables[0]
        self._applied_steps_by_table = applied_steps_by_table or {
            self._selected_table: []
        }

        self._props['tablesProp'] = self._tables
        self._props['selectedTable'] = self._selected_table
        self._props['appliedStepsByTable'] = self._applied_steps_by_table

    def set_selected_table(self, table_name: str) -> None:
        """Set active selected query table."""
        self._selected_table = table_name
        self._props['selectedTable'] = table_name
        self.update()

    def update_steps(self, table_name: str, steps: List[Dict[str, Any]]) -> None:
        """Update steps for a specific table query."""
        self._applied_steps_by_table[table_name] = steps
        self._props['appliedStepsByTable'] = self._applied_steps_by_table
        self.update()
