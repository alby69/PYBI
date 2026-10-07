"""Python wrapper for Vue Grid Layout Dashboard component."""

from typing import Dict, List, Any, Callable, Optional
from nicegui import ui

class DashboardGrid(ui.element, component='dashboard_grid.js'):
    """DashboardGrid wraps grid-layout-plus Vue component for dashboard visual widgets."""

    def __init__(
        self,
        layout: Optional[List[Dict[str, Any]]] = None,
        col_num: int = 12,
        row_height: int = 60,
        is_draggable: bool = True,
        is_resizable: bool = True
    ) -> None:
        super().__init__()

        # Polyfill process.env for browser ESM compatibility
        ui.add_head_html('<script>window.process = window.process || { env: { NODE_ENV: "production" } };</script>')

        self._layout = layout or []
        self._props['layout'] = self._layout
        self._props['colNum'] = col_num
        self._props['rowHeight'] = row_height
        self._props['isDraggable'] = is_draggable
        self._props['isResizable'] = is_resizable

    @property
    def layout(self) -> List[Dict[str, Any]]:
        return self._layout

    @layout.setter
    def layout(self, value: List[Dict[str, Any]]) -> None:
        self._layout = value
        self._props['layout'] = value
        self.update()

    def on_layout_updated(self, handler: Callable) -> 'DashboardGrid':
        self.on('layout_updated', handler)
        return self

    def on_change(self, handler: Callable) -> 'DashboardGrid':
        self.on('change', handler)
        return self

    def on_edit_widget(self, handler: Callable) -> 'DashboardGrid':
        self.on('edit_widget', handler)
        return self
