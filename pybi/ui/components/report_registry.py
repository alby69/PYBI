"""NiceGUI registrations for the Power BI style Report View component suite."""

from pathlib import Path
from typing import Optional

from nicegui import ui
from nicegui.dependencies import libraries, register_library

COMPONENTS_DIR = Path(__file__).resolve().parent
UI_DIR = COMPONENTS_DIR.parent
STORE_DIR = UI_DIR / "stores"
REPORT_DIR = COMPONENTS_DIR / "report"
DATA_DIR = COMPONENTS_DIR / "data"
SHELL_DIR = COMPONENTS_DIR / "shell"


def _register_store(path: Path, import_name: str) -> None:
    """Register a JS store once, even if this module is imported repeatedly."""
    for library in libraries.values():
        if library.name == import_name and library.path == path:
            return
    register_library(path, import_name=import_name, max_time=path.stat().st_mtime)


def _component_path(directory: Path, filename: str) -> str:
    return str(directory / filename)


_register_store(STORE_DIR / "reportStore.js", "pybi-report-store")
_register_store(STORE_DIR / "themeStore.js", "pybi-theme-store")
_register_store(STORE_DIR / "localeStore.js", "pybi-locale-store")


class ReportMainShell(ui.element, component=_component_path(SHELL_DIR, "MainShell.vue")):
    """Full Report View shell: ribbon, panes, canvas, page tabs and data view."""

    def __init__(self, project_id: str = "default") -> None:
        super().__init__()
        self._project_id = project_id
        self._props["projectId"] = project_id

    def set_project_id(self, project_id: str) -> None:
        self._project_id = project_id or "default"
        self._props["projectId"] = self._project_id
        self.update()


class ReportCanvas(ui.element, component=_component_path(REPORT_DIR, "ReportCanvas.vue")):
    """Power BI style report canvas with drag, resize, lasso and smart guides."""

    def __init__(self, project_id: str = "default") -> None:
        super().__init__()
        self._props["projectId"] = project_id


class FiltersPane(ui.element, component=_component_path(REPORT_DIR, "FiltersPane.vue")):
    """Three-level filters pane (visual, page and report)."""


class VisualizationsPane(ui.element, component=_component_path(REPORT_DIR, "VisualizationsPane.vue")):
    """Visual type picker, field buckets and formatting tabs."""


class FormattingPane(ui.element, component=_component_path(REPORT_DIR, "FormattingPane.vue")):
    """Visual/page formatting properties with conditional formatting."""


class VisualHeader(ui.element, component=_component_path(REPORT_DIR, "VisualHeader.vue")):
    """Contextual visual header with focus, filters, export and menu actions."""


class VisualRenderer(ui.element, component=_component_path(REPORT_DIR, "VisualRenderer.vue")):
    """Renderer for charts, tables, cards, gauges, slicers and shapes."""


class PageTabBar(ui.element, component=_component_path(REPORT_DIR, "PageTabBar.vue")):
    """Bottom report page tabs with rename, reorder and context menu."""


class DataPane(ui.element, component=_component_path(DATA_DIR, "DataPane.vue")):
    """Power BI Fields/Data pane with tables, columns, measures and drag payloads."""


class DataTableView(ui.element, component=_component_path(DATA_DIR, "DataTableView.vue")):
    """Sortable, searchable data grid for the Data View."""


class LanguageSelector(ui.element, component=_component_path(SHELL_DIR, "LanguageSelector.vue")):
    """Runtime language selector for the report shell status bar."""


ReportElement = Optional[ReportMainShell]

__all__ = [
    "DataPane",
    "DataTableView",
    "FiltersPane",
    "FormattingPane",
    "LanguageSelector",
    "PageTabBar",
    "ReportCanvas",
    "ReportElement",
    "ReportMainShell",
    "VisualHeader",
    "VisualRenderer",
    "VisualizationsPane",
]
