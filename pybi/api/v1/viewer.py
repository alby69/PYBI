"""FastAPI router for Public Read-Only Viewer endpoints in PyBI v1 REST API."""

from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, status

from pybi.core.storage import default_storage
from pybi.dashboard.binding import default_binder
import pybi.storage.project_manager as pm

router = APIRouter(prefix="/api/v1/viewer", tags=["Viewer"])


@router.get("/health")
def viewer_health() -> Dict[str, str]:
    """Health check endpoint for viewer API."""
    return {"status": "ok", "service": "pybi-viewer-api"}


@router.get("/projects/{project_id}")
def get_published_project(project_id: str) -> Dict[str, Any]:
    """Fetch published dashboard layout and schema for read-only viewing."""
    if not default_storage.project_exists(project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found")

    dashboards = pm.load_dashboard_layout(project_id)
    layout = dashboards.get("layout", [])

    return {
        "project_id": project_id,
        "status": "published",
        "layout": layout,
        "tables": default_binder.list_sources(),
    }


@router.get("/{project_id}/dashboards/{dashboard_id}/data")
def get_viewer_dashboard_data(project_id: str, dashboard_id: str) -> Dict[str, Any]:
    """Optimized read-only endpoint returning aggregated widget data ready for rendering."""
    if not default_storage.project_exists(project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found")

    layout = default_storage.load_dashboard(project_id, dashboard_id)
    if layout is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dashboard '{dashboard_id}' not found in project '{project_id}'",
        )

    widget_data: List[Dict[str, Any]] = []
    registered_sources = set(default_binder.list_sources())

    for item in layout:
        w_id = item.get("i", "w")
        w_type = item.get("widget_type", "chart")
        config = item.get("config", {})

        data_entry = {
            "id": w_id,
            "type": w_type,
            "config": config,
            "rows": [],
            "columns": [],
        }

        tbl_name = config.get("table_name") or config.get("source_name")
        if tbl_name and tbl_name in registered_sources:
            try:
                df = default_binder.get_source_data(tbl_name)
                data_entry["columns"] = df.columns
                data_entry["rows"] = df.head(100).to_dicts()
            except Exception:
                pass

        widget_data.append(data_entry)

    return {
        "project_id": project_id,
        "dashboard_id": dashboard_id,
        "widgets": widget_data,
        "sources": default_binder.list_sources(),
    }
