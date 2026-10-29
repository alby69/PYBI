"""FastAPI router for Project Management endpoints in PyBI v1 REST API."""

from typing import List, Union

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from pybi.api.schemas import (
    ProjectCreate,
    ProjectResponse,
    FileUploadResponse,
    FileListResponse,
)
from pybi.api.v1.models import (
    MessageResponse,
    ProjectCreateRequest,
    ProjectListResponse,
    ProjectSummary,
    ProjectUpdateRequest,
)
import pybi.storage.project_manager as pm
from pybi.core.storage import default_storage, sanitize_project_id

router = APIRouter(prefix="/api/v1/projects", tags=["Projects"])


def _to_project_response(data: dict) -> ProjectResponse:
    """Helper to construct ProjectResponse from storage dictionary."""
    pid = data.get("project_id") or data.get("id") or "unknown"
    return ProjectResponse(
        id=pid,
        name=data.get("name", pid),
        description=data.get("description"),
        etl_dag=data.get("etl_dag", {"nodes": [], "edges": []}),
        dashboards=data.get("dashboards", []),
        dashboard_layout=data.get("dashboard_layout"),
        created_at=data.get("created_at"),
        updated_at=data.get("updated_at"),
    )


@router.get("", response_model=ProjectListResponse)
def list_projects() -> ProjectListResponse:
    """List all saved project IDs and summaries."""
    project_ids = default_storage.list_projects()
    summaries = []
    for pid in project_ids:
        try:
            proj = pm.get_project(pid)
            summaries.append(
                ProjectSummary(
                    project_id=pid,
                    name=proj.get("name") or pid,
                    description=proj.get("description"),
                    created_at=proj.get("created_at"),
                    updated_at=proj.get("updated_at"),
                )
            )
        except Exception:
            summaries.append(ProjectSummary(project_id=pid, name=pid))

    return ProjectListResponse(projects=summaries, total=len(summaries))


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(req: Union[ProjectCreate, ProjectCreateRequest]) -> ProjectResponse:
    """Create a new project."""
    raw_pid = getattr(req, "project_id", None) or getattr(req, "name", "project")
    pid = sanitize_project_id(raw_pid)

    if default_storage.project_exists(pid):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project with ID '{pid}' already exists",
        )

    try:
        saved = pm.create_project(
            name=req.name,
            project_id=pid,
            description=req.description,
        )
        return _to_project_response(saved)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str) -> ProjectResponse:
    """Load project details by project_id."""
    try:
        data = pm.get_project(project_id)
        return _to_project_response(data)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found")


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: str, req: ProjectUpdateRequest) -> ProjectResponse:
    """Update project name or description."""
    try:
        updated = pm.update_project(
            project_id=project_id,
            name=req.name,
            description=req.description,
        )
        return _to_project_response(updated)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found")


@router.delete("/{project_id}", response_model=MessageResponse)
def delete_project(project_id: str) -> MessageResponse:
    """Delete project and associated files."""
    deleted = pm.delete_project(project_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found")
    return MessageResponse(message=f"Project '{project_id}' deleted successfully", success=True)


@router.post("/{project_id}/files", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_project_file(project_id: str, file: UploadFile = File(...)) -> FileUploadResponse:
    """Upload a data source file (CSV, Parquet, SQLite) into project data folder."""
    if not default_storage.project_exists(project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found")

    content = await file.read()
    file_path = default_storage.save_uploaded_file(project_id, file.filename, content)
    return FileUploadResponse(
        filename=file.filename,
        file_path=file_path,
        size_bytes=len(content),
        message=f"File '{file.filename}' uploaded successfully to project '{project_id}'",
    )


@router.get("/{project_id}/files", response_model=FileListResponse)
def list_project_files(project_id: str) -> FileListResponse:
    """List data source files stored in project data directory."""
    if not default_storage.project_exists(project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found")

    files = default_storage.list_project_files(project_id)
    return FileListResponse(project_id=project_id, files=files)


@router.delete("/{project_id}/files/{filename}", response_model=MessageResponse)
def delete_project_file(project_id: str, filename: str) -> MessageResponse:
    """Delete a data source file from project data folder."""
    if not default_storage.project_exists(project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found")

    deleted = default_storage.delete_project_file(project_id, filename)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File '{filename}' not found in project '{project_id}'",
        )
    return MessageResponse(message=f"File '{filename}' deleted from project '{project_id}'", success=True)
