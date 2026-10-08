"""FastAPI router for Public Read-Only Viewer endpoints in PyBI v1 REST API."""

from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, status

from pybi.core.storage import default_storage
from pybi.dashboard.binding import default_binder
import pybi.storage.project_manager as pm
from pybi.semantic.engine import SemanticQueryResolver
from pybi.semantic.models import SemanticQueryRequest, SemanticQueryResponse

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


@router.post("/{project_id}/semantic-query", response_model=SemanticQueryResponse)
def execute_semantic_query(project_id: str, request: SemanticQueryRequest) -> SemanticQueryResponse:
    """Execute a semantic query against a project's registered data sources or semantic models."""
    if not default_storage.project_exists(project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found")

    resolver = SemanticQueryResolver()
    source_name = request.source_table or request.model_name
    source_df = None

    if source_name and source_name in default_binder.list_sources():
        try:
            source_df = default_binder.get_source_data(source_name)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Error loading source '{source_name}': {e}")

    try:
        response = resolver.execute(request, source_df=source_df)
        return response
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Semantic query execution failed: {e}")
