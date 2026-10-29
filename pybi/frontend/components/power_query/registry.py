"""NiceGUI registrations for the Power Query Vue component suite."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from nicegui import ui
from nicegui.dependencies import register_library

COMPONENT_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = COMPONENT_DIR.parents[1]
STORE_PATH = FRONTEND_DIR / "stores" / "uiStore.js"

register_library(STORE_PATH, import_name="pybi-store", max_time=STORE_PATH.stat().st_mtime)


def _component_path(filename: str) -> str:
    return str(COMPONENT_DIR / filename)


class PowerQueryRibbon(ui.element, component=_component_path("PowerQueryRibbon.vue")):
    pass


class RibbonToolbar(ui.element, component=_component_path("RibbonToolbar.vue")):
    pass


class FormulaBar(ui.element, component=_component_path("FormulaBar.vue")):
    pass


class QueriesPane(ui.element, component=_component_path("QueriesPane.vue")):
    pass


class DataGridPreview(ui.element, component=_component_path("DataGridPreview.vue")):
    pass


class ColumnHeader(ui.element, component=_component_path("ColumnHeader.vue")):
    pass


class ColumnHeaderMenu(ui.element, component=_component_path("ColumnHeaderMenu.vue")):
    pass


class DataProfilingBar(ui.element, component=_component_path("DataProfilingBar.vue")):
    pass


class AppliedStepsPanel(ui.element, component=_component_path("AppliedStepsPanel.vue")):
    pass


class DiagramView(ui.element, component=_component_path("DiagramView.vue")):
    pass


class FilterModal(ui.element, component=_component_path("FilterModal.vue")):
    pass


class GroupByModal(ui.element, component=_component_path("GroupByModal.vue")):
    pass


class MergeJoinModal(ui.element, component=_component_path("MergeJoinModal.vue")):
    pass


class CustomColumnModal(ui.element, component=_component_path("CustomColumnModal.vue")):
    pass


class AdvancedEditorModal(ui.element, component=_component_path("AdvancedEditorModal.vue")):
    pass


class ChooseColumnsModal(ui.element, component=_component_path("ChooseColumnsModal.vue")):
    pass


class ReplaceValuesModal(ui.element, component=_component_path("ReplaceValuesModal.vue")):
    pass


class SplitColumnModal(ui.element, component=_component_path("SplitColumnModal.vue")):
    pass


class ConditionalColumnModal(ui.element, component=_component_path("ConditionalColumnModal.vue")):
    pass


class PowerQueryEditor(ui.element, component=_component_path("PowerQueryEditor.vue")):
    """NiceGUI element wrapping the multi-panel Power Query Editor Vue component."""

    def __init__(
        self,
        tables: Optional[List[str]] = None,
        selected_table: Optional[str] = None,
        applied_steps_by_table: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        project_id: str = "default",
    ) -> None:
        super().__init__()

        ui.add_head_html('<script>window.process = window.process || { env: { NODE_ENV: "production" } };</script>')

        self._tables = tables or ["sales_data.csv"]
        self._selected_table = selected_table or self._tables[0]
        self._applied_steps_by_table = applied_steps_by_table or {self._selected_table: []}
        self._project_id = project_id

        self._sync_props()

    def _sync_props(self) -> None:
        self._props["tablesProp"] = self._tables
        self._props["selectedTable"] = self._selected_table
        self._props["appliedStepsByTable"] = self._applied_steps_by_table
        self._props["projectId"] = self._project_id

    def set_tables(self, tables: List[str]) -> None:
        self._tables = tables or []
        self._props["tablesProp"] = self._tables
        self.update()

    def set_selected_table(self, table_name: str) -> None:
        self._selected_table = table_name
        self._props["selectedTable"] = table_name
        self.update()

    def set_project_id(self, project_id: str) -> None:
        self._project_id = project_id or "default"
        self._props["projectId"] = self._project_id
        self.update()

    def update_steps(self, table_name: str, steps: List[Dict[str, Any]]) -> None:
        self._applied_steps_by_table[table_name] = steps
        self._props["appliedStepsByTable"] = self._applied_steps_by_table
        self.update()

    def set_applied_steps(self, applied_steps_by_table: Dict[str, List[Dict[str, Any]]]) -> None:
        self._applied_steps_by_table = applied_steps_by_table or {}
        self._props["appliedStepsByTable"] = self._applied_steps_by_table
        self.update()
