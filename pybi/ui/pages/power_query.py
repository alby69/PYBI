"""Power Query Editor page built with the Vue component suite."""

from pathlib import Path
from typing import Any, Dict, List, Tuple

from nicegui import ui

from pybi.core.storage import default_storage
from pybi.frontend.components.power_query.power_query_editor import PowerQueryEditor
from pybi.ui.components.navbar import render_navbar
from pybi.ui.components.project_manager import ProjectManager

SUPPORTED_EXTENSIONS = {".csv", ".parquet", ".json", ".sqlite", ".db"}


def _project_files(project_id: str) -> List[str]:
    if not project_id or not default_storage.project_exists(project_id):
        return []
    files = default_storage.list_project_files(project_id)
    return sorted(
        name for name in files
        if Path(name).suffix.lower() in SUPPORTED_EXTENSIONS
    )


def _load_saved_query(project_id: str) -> Dict[str, Any]:
    if not project_id or not default_storage.project_exists(project_id):
        return {}
    try:
        dag = default_storage.load_etl_dag(project_id)
    except Exception:
        return {}
    if not isinstance(dag, dict):
        return {}
    return dag


def _editor_state(project_id: str) -> Tuple[List[str], str, Dict[str, List[Dict[str, Any]]]]:
    tables = _project_files(project_id)
    saved = _load_saved_query(project_id)
    source = saved.get("source") or {}
    source_table = source.get("table_name") or source.get("path") or saved.get("query_name")
    steps = saved.get("steps") or []

    applied: Dict[str, List[Dict[str, Any]]] = {}
    if source_table:
        if source_table not in tables and isinstance(source_table, str):
            tables.append(source_table)
        applied[source_table] = steps
    elif tables:
        applied[tables[0]] = []

    selected = source_table if source_table in tables else (tables[0] if tables else "")
    return tables, selected, applied


def create_power_query_page():
    render_navbar(active="/power-query")

    with ui.row().classes("w-full items-end justify-between q-mt-sm"):
        with ui.column().classes("gap-0"):
            ui.label("Power Query Editor").classes("text-2xl font-bold text-slate-900")
            ui.label(
                "Visual transformation workspace with ribbon, queries pane, profiling grid, diagram view and applied steps."
            ).classes("text-sm text-slate-600")
        ui.button(
            "Classic ETL Editor",
            icon="swap_horiz",
            on_click=lambda: ui.navigate.to("/etl-editor"),
        ).props("flat dense color=slate")

    state: Dict[str, Any] = {"project": ""}
    editor_container = ui.column().classes("w-full overflow-hidden q-mt-sm").style(
        "height: calc(100vh - 190px); min-height: 560px;"
    )

    def refresh_editor(project_id: str):
        state["project"] = project_id
        editor_container.clear()
        tables, selected, applied = _editor_state(project_id)
        with editor_container:
            if not tables:
                with ui.card().classes("w-full items-center q-pa-lg border border-dashed border-slate-300"):
                    ui.icon("upload_file", size="36px").classes("text-slate-400")
                    ui.label("No data source available for this project.").classes("text-sm font-semibold text-slate-700")
                    ui.label("Upload a CSV, Parquet, JSON or SQLite file using the button above.").classes(
                        "text-xs text-slate-500"
                    )
            editor = PowerQueryEditor(
                tables=tables,
                selected_table=selected,
                applied_steps_by_table=applied,
                project_id=project_id,
            ).classes("w-full h-full")
            editor.on(
                "request-get-data",
                lambda: ui.notify("Use the Upload button in the page header to add a data source.", type="info"),
            )
        status_label.set_text(
            f"{len(tables)} data source(s) · project '{project_id or 'none'}'"
        )

    def handle_project_switch(project_id, action):
        status_label.set_text(f"Project: {project_id or 'none'}")
        refresh_editor(project_id)

    async def handle_upload(event):
        project_id = state.get("project") or project_manager.project_id
        if not project_id:
            ui.notify("Select or create a project before uploading data.", type="warning")
            return
        try:
            content = await event.file.read()
            saved_path = default_storage.save_uploaded_file(project_id, event.file.name, content)
            ui.notify(f"Uploaded {event.file.name} to {saved_path}", type="positive")
            refresh_editor(project_id)
        except Exception as err:
            ui.notify(f"Upload failed: {err}", type="negative")

    with ui.row().classes("w-full items-center gap-3 flex-wrap bg-slate-50 border border-slate-200 rounded px-3 py-2"):
        project_manager = ProjectManager(value="", on_switch=handle_project_switch)
        ui.separator().props("vertical")
        ui.upload(
            on_upload=handle_upload,
            label="Upload data source",
            auto_upload=True,
            multiple=False,
        ).props("accept=.csv,.parquet,.json,.sqlite,.db dense outlined").classes("w-64")
        ui.button(
            "Reload",
            icon="refresh",
            on_click=lambda: refresh_editor(project_manager.project_id),
        ).props("flat dense")
        ui.space()
        status_label = ui.label("").classes("text-xs font-semibold text-slate-600")

    refresh_editor(project_manager.project_id)
