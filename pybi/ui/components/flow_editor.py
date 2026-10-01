"""Python wrapper for Vue Flow ETL Editor component."""

from typing import Dict, List, Any, Callable, Optional
from nicegui import ui

class FlowEditor(ui.element, component='flow_editor.js'):
    """FlowEditor wraps Vue Flow component for visual ETL DAG creation."""

    def __init__(self, nodes: Optional[List[Dict[str, Any]]] = None, edges: Optional[List[Dict[str, Any]]] = None) -> None:
        super().__init__()

        # Polyfill process.env for browser ESM compatibility
        ui.add_head_html('<script>window.process = window.process || { env: { NODE_ENV: "production" } };</script>')
        # Inject Vue Flow stylesheets
        ui.add_head_html('<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@vue-flow/core@1.42.0/dist/style.css">')
        ui.add_head_html('<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@vue-flow/core@1.42.0/dist/theme-default.css">')

        self._nodes = nodes or []
        self._edges = edges or []
        self._props['nodes'] = self._nodes
        self._props['edges'] = self._edges

    @property
    def nodes(self) -> List[Dict[str, Any]]:
        return self._nodes

    @nodes.setter
    def nodes(self, value: List[Dict[str, Any]]) -> None:
        self._nodes = value
        self._props['nodes'] = value
        self.update()

    @property
    def edges(self) -> List[Dict[str, Any]]:
        return self._edges

    @edges.setter
    def edges(self, value: List[Dict[str, Any]]) -> None:
        self._edges = value
        self._props['edges'] = value
        self.update()

    def on_node_drag_stop(self, handler: Callable) -> 'FlowEditor':
        self.on('node_drag_stop', handler)
        return self

    def on_connect(self, handler: Callable) -> 'FlowEditor':
        self.on('connect', handler)
        return self

    def on_change(self, handler: Callable) -> 'FlowEditor':
        self.on('change', handler)
        return self
