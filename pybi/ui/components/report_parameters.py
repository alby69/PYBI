"""Python wrapper for Report Parameters Panel Vue component."""

from typing import Any, Dict, List, Optional
from nicegui import ui


class ReportParameters(ui.element, component='report_parameters.js'):
    """ReportParameters wraps collapsible left sidebar for report parameters with cascading options."""

    def __init__(
        self,
        project_id: str = "default",
        parameters: Optional[List[Dict[str, Any]]] = None,
        initial_values: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__()

        # Polyfill process.env for browser ESM compatibility
        ui.add_head_html('<script>window.process = window.process || { env: { NODE_ENV: "production" } };</script>')

        self._project_id = project_id
        self._parameters = parameters or []
        self._initial_values = initial_values or {}

        self._props['projectId'] = self._project_id
        self._props['parameters'] = self._parameters
        self._props['initialValues'] = self._initial_values

    def update_parameters(self, parameters: List[Dict[str, Any]]) -> None:
        """Update parameter definitions list."""
        self._parameters = parameters
        self._props['parameters'] = parameters
        self.update()
