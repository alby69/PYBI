"""Python wrapper for Vue DynamicRenderer component."""

from typing import Any, Dict, List, Optional
from nicegui import ui


class DynamicRenderer(ui.element, component='dynamic_renderer.js'):
    """DynamicRenderer interprets JSON UI schemas and renders dynamic Vue / Quasar components."""

    def __init__(
        self,
        schema: Optional[Any] = None,
        page_name: Optional[str] = None
    ) -> None:
        super().__init__()
        self._schema = schema
        self._page_name = page_name or ""
        self._props['schema'] = self._schema
        self._props['pageName'] = self._page_name

    @property
    def schema(self) -> Optional[Any]:
        return self._schema

    @schema.setter
    def schema(self, value: Optional[Any]) -> None:
        self._schema = value
        self._props['schema'] = value
        self.update()

    @property
    def page_name(self) -> str:
        return self._page_name

    @page_name.setter
    def page_name(self, value: str) -> None:
        self._page_name = value
        self._props['pageName'] = value
        self.update()
