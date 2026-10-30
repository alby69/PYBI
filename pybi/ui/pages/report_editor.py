"""Power BI style Report View page (canvas, pages, panes and Data View)."""

from pathlib import Path

from nicegui import ui

from pybi.ui.components.navbar import render_navbar
from pybi.ui.components.project_manager import ProjectManager
from pybi.ui.components.report_registry import ReportMainShell

THEME_CSS_PATH = Path(__file__).resolve().parents[1] / "assets" / "powerbi-theme.css"


def create_report_editor_page(initial_project: str = "default") -> None:
    """Render the full Report View shell for the selected project."""
    if THEME_CSS_PATH.exists():
        ui.add_css(THEME_CSS_PATH.read_text(encoding="utf-8"))

    render_navbar(active="/report")

    with ui.column().classes("w-full gap-0 p-0").style("height: calc(100vh - 112px); overflow: hidden;"):
        shell_holder = {"shell": None}

        def handle_project_switch(project_id: str, action: str) -> None:
            shell = shell_holder.get("shell")
            if shell is not None:
                shell.set_project_id(project_id or "default")
            if action in {"create", "delete", "select", "rename"}:
                ui.notify(f'Progetto "{project_id}" caricato', type="info")

        with ui.row().classes(
            "w-full shrink-0 items-center gap-3 border-b border-slate-300 bg-slate-100 px-3 py-1"
        ):
            project_manager = ProjectManager(value=initial_project or "default", on_switch=handle_project_switch)
            ui.label("Report View").classes("text-sm font-bold text-slate-700")
            ui.label(
                "Canvas, pagine, filtri, visualizzazioni, formattazione e vista dati in stile Power BI."
            ).classes("text-xs text-slate-500")
            ui.space()

        shell = ReportMainShell(project_id=project_manager.project_id)
        shell.classes("w-full flex-1 min-h-0").style("min-height: 0;")
        shell_holder["shell"] = shell
