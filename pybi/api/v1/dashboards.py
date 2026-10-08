"""FastAPI router for Dashboard Layout operations in PyBI v1 REST API."""

from fastapi import APIRouter, HTTPException, status
from typing import List

from pybi.core.storage import default_storage
from pybi.api.v1.models import (
    DashboardListResponse,
    DashboardSchema,
    MessageResponse,
    SaveDashboardRequest,
)

router = APIRouter(prefix="/api/v1/projects/{project_id}/dashboards", tags=["Dashboards"])


@router.get("", response_model=DashboardListResponse)
def list_dashboards(project_id: str) -> DashboardListResponse:
    """List saved dashboards for project."""
    if not default_storage.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

    raw_dashboards = default_storage.list_dashboards(project_id)
    schemas = []
    for d in raw_dashboards:
        did = d.get("id", "dash_1")
        layout = default_storage.load_dashboard(project_id, did) or []
        schemas.append(DashboardSchema(id=did, name=d.get("name") or did, layout=layout))

    return DashboardListResponse(project_id=project_id, dashboards=schemas)


@router.get("/{dashboard_id}", response_model=DashboardSchema)
def get_dashboard(project_id: str, dashboard_id: str) -> DashboardSchema:
    """Load specific dashboard layout by dashboard_id."""
    if not default_storage.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

    layout = default_storage.load_dashboard(project_id, dashboard_id)
    if layout is None:
        raise HTTPException(
            status_code=404,
            detail=f"Dashboard '{dashboard_id}' not found in project '{project_id}'",
        )

    dashboards = default_storage.list_dashboards(project_id)
    name = dashboard_id
    for d in dashboards:
        if d.get("id") == dashboard_id:
            name = d.get("name", dashboard_id)

    return DashboardSchema(id=dashboard_id, name=name, layout=layout)


@router.put("/{dashboard_id}", response_model=MessageResponse)
def save_dashboard(project_id: str, dashboard_id: str, req: SaveDashboardRequest) -> MessageResponse:
    """Save or update dashboard layout grid configuration."""
    name = req.name or dashboard_id
    default_storage.save_dashboard(
        project_id=project_id,
        dashboard_id=dashboard_id,
        name=name,
        layout=req.layout,
    )
    return MessageResponse(
        message=f"Dashboard '{dashboard_id}' saved successfully for project '{project_id}'",
        success=True,
    )


@router.delete("/{dashboard_id}", response_model=MessageResponse)
def delete_dashboard(project_id: str, dashboard_id: str) -> MessageResponse:
    """Delete dashboard from project."""
    deleted = default_storage.delete_dashboard(project_id, dashboard_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Dashboard '{dashboard_id}' not found in project '{project_id}'",
        )
    return MessageResponse(
        message=f"Dashboard '{dashboard_id}' deleted from project '{project_id}'",
        success=True,
    )
