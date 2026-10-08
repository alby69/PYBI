"""FastAPI router for Project Management endpoints in PyBI v1 REST API."""

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from typing import Optional

from pybi.core.storage import default_storage
from pybi.api.v1.models import (
    FileListResponse,
    FileUploadResponse,
    MessageResponse,
    ProjectCreateRequest,
    ProjectListResponse,
    ProjectResponse,
    ProjectSummary,
    ProjectUpdateRequest,
)

router = APIRouter(prefix="/api/v1/projects", tags=["Projects"])


def _to_project_response(data: dict) -> ProjectResponse:
    """Helper to construct ProjectResponse from storage dictionary."""
    return ProjectResponse(
        project_id=data.get("project_id", "unknown"),
        name=data.get("name", ""),
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
            proj = default_storage.load_project(pid)
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
def create_project(req: ProjectCreateRequest) -> ProjectResponse:
    """Create a new project."""
    if default_storage.project_exists(req.project_id):
        raise HTTPException(
            status_code=400,
            detail=f"Project with ID '{req.project_id}' already exists",
        )

    saved = default_storage.save_project(
        project_id=req.project_id,
        name=req.name,
        etl_dag={"nodes": [], "edges": []},
        dashboards=[],
    )
    if req.description:
        saved["description"] = req.description
    return _to_project_response(saved)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str) -> ProjectResponse:
    """Load project details by project_id."""
    if not default_storage.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
    data = default_storage.load_project(project_id)
    return _to_project_response(data)


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: str, req: ProjectUpdateRequest) -> ProjectResponse:
    """Update project name or description."""
    if not default_storage.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

    existing = default_storage.load_project(project_id)
    new_name = req.name if req.name is not None else existing.get("name", project_id)
    updated = default_storage.save_project(
        project_id=project_id,
        name=new_name,
        etl_dag=existing.get("etl_dag"),
        dashboards=existing.get("dashboards"),
    )
    if req.description is not None:
        updated["description"] = req.description
    return _to_project_response(updated)


@router.delete("/{project_id}", response_model=MessageResponse)
def delete_project(project_id: str) -> MessageResponse:
    """Delete project and associated files."""
    deleted = default_storage.delete_project(project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
    return MessageResponse(message=f"Project '{project_id}' deleted successfully", success=True)


@router.post("/{project_id}/files", response_model=FileUploadResponse)
async def upload_project_file(project_id: str, file: UploadFile = File(...)) -> FileUploadResponse:
    """Upload a data source file (CSV, Parquet, SQLite) into project data folder."""

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
    files = default_storage.list_project_files(project_id)
    return FileListResponse(project_id=project_id, files=files)


@router.delete("/{project_id}/files/{filename}", response_model=MessageResponse)
def delete_project_file(project_id: str, filename: str) -> MessageResponse:
    """Delete a data source file from project data folder."""
    deleted = default_storage.delete_project_file(project_id, filename)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"File '{filename}' not found in project '{project_id}'",
        )
    return MessageResponse(message=f"File '{filename}' deleted from project '{project_id}'", success=True)
