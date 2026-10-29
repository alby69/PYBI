"""FastAPI router for File operations in PyBI v1 REST API."""

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from pybi.api.schemas import FileListResponse, FileUploadResponse
from pybi.api.v1.models import MessageResponse
from pybi.core.storage import default_storage

router = APIRouter(prefix="/api/v1/projects/{project_id}/files", tags=["Files"])


@router.get("", response_model=FileListResponse)
def list_files(project_id: str) -> FileListResponse:
    """List data source files stored in project data directory."""
    if not default_storage.project_exists(project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found")

    files = default_storage.list_project_files(project_id)
    return FileListResponse(project_id=project_id, files=files)


@router.post("", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(project_id: str, file: UploadFile = File(...)) -> FileUploadResponse:
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


@router.delete("/{filename}", response_model=MessageResponse)
def delete_file(project_id: str, filename: str) -> MessageResponse:
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
