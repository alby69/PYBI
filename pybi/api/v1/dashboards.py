"""FastAPI router for Dashboard Layout operations in PyBI v1 REST API."""

from typing import Any, Dict, List, Optional, Union
import uuid

from fastapi import APIRouter, HTTPException, status

from pybi.api.schemas import DashboardCreateRequest, DashboardSaveRequest
from pybi.api.v1.models import (
    DashboardListResponse,
    DashboardSchema,
    MessageResponse,
    SaveDashboardRequest,
)
from pybi.core.storage import default_storage
import pybi.storage.project_manager as pm

router = APIRouter(prefix="/api/v1/projects/{project_id}/dashboards", tags=["Dashboards"])


@router.get("", response_model=DashboardListResponse)
def list_dashboards(project_id: str) -> DashboardListResponse:
    """List saved dashboards for project."""
    if not default_storage.project_exists(project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found")

    raw_dashboards = default_storage.list_dashboards(project_id)
    schemas = []
    for d in raw_dashboards:
        did = d.get("id", "dash_1")
        dash_data = pm.load_dashboard_layout(project_id, did)
        layout = dash_data.get("layout", [])
        schemas.append(DashboardSchema(id=did, name=d.get("name") or did, layout=layout))

    return DashboardListResponse(project_id=project_id, dashboards=schemas)


@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
def create_dashboard(project_id: str, req: DashboardCreateRequest) -> Dict[str, Any]:
    """Create a new dashboard for project and return new dashboard_id."""
    if not default_storage.project_exists(project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found")

    new_id = f"dash_{uuid.uuid4().hex[:6]}"
    pm.save_dashboard_layout(
        project_id=project_id,
        layout=[],
        dashboard_id=new_id,
        name=req.name,
    )
    return {
        "dashboard_id": new_id,
        "id": new_id,
        "name": req.name,
        "message": f"Dashboard '{req.name}' created with ID '{new_id}'",
    }


@router.get("/{dashboard_id}", response_model=Dict[str, Any])
def get_dashboard(project_id: str, dashboard_id: str) -> Dict[str, Any]:
    """Load specific dashboard layout and bindings by dashboard_id."""
    if not default_storage.project_exists(project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found")

    layout = default_storage.load_dashboard(project_id, dashboard_id)
    if layout is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dashboard '{dashboard_id}' not found in project '{project_id}'",
        )

    dashboards = default_storage.list_dashboards(project_id)
    name = dashboard_id
    for d in dashboards:
        if d.get("id") == dashboard_id:
            name = d.get("name", dashboard_id)

    return {
        "id": dashboard_id,
        "name": name,
        "layout": layout,
        "bindings": {},
    }


@router.put("/{dashboard_id}", response_model=MessageResponse)
def save_dashboard(
    project_id: str,
    dashboard_id: str,
    req: Union[DashboardSaveRequest, SaveDashboardRequest],
) -> MessageResponse:
    """Save or update dashboard layout grid configuration and bindings."""
    if not default_storage.project_exists(project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found")

    name = req.name or dashboard_id
    bindings = getattr(req, "bindings", {}) or {}

    pm.save_dashboard_layout(
        project_id=project_id,
        layout=req.layout,
        dashboard_id=dashboard_id,
        name=name,
        bindings=bindings,
    )
    return MessageResponse(
        message=f"Dashboard '{dashboard_id}' saved successfully for project '{project_id}'",
        success=True,
    )


@router.delete("/{dashboard_id}", response_model=MessageResponse)
def delete_dashboard(project_id: str, dashboard_id: str) -> MessageResponse:
    """Delete dashboard from project."""
    if not default_storage.project_exists(project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found")

    deleted = pm.delete_dashboard(project_id, dashboard_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dashboard '{dashboard_id}' not found in project '{project_id}'",
        )
    return MessageResponse(
        message=f"Dashboard '{dashboard_id}' deleted from project '{project_id}'",
        success=True,
    )
