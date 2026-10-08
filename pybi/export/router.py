"""FastAPI router for Phase 5 Publishing & Export Engine REST API."""

from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from pybi.export.engine import default_export_engine

router = APIRouter(prefix="/api", tags=["export"])


class ExportRequest(BaseModel):
    """Payload model for project export requests."""

    format: str = Field(default="html", description="Export format: pdf | html | md | csv")
    template_id: Optional[str] = Field(default=None, description="Jinja2 template filename")
    filter_context: Optional[Dict[str, Any]] = Field(default=None, description="Active filter context rules")
    ai_compilation_prompt: Optional[str] = Field(default=None, description="Prompt for AI-assisted compilation")
    payload: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Export payload (widgets, tables, title)")


@router.post("/projects/{project_id}/export")
def create_export_job(project_id: str, req: ExportRequest) -> Dict[str, Any]:
    """Initiate an asynchronous export job."""
    payload = req.payload or {}
    if "title" not in payload:
        payload["title"] = f"PyBI Export - {project_id}"

    export_id = default_export_engine.submit_export_job(
        project_id=project_id,
        payload=payload,
        filter_context=req.filter_context,
        export_format=req.format,
        template_id=req.template_id,
        ai_prompt=req.ai_compilation_prompt,
    )

    status_info = default_export_engine.get_job_status(export_id)
    return {
        "export_id": export_id,
        "status": status_info.get("status", "pending") if status_info else "pending",
        "message": f"Export job submitted successfully for project '{project_id}'",
        "status_url": f"/api/exports/{export_id}/status",
        "download_url": f"/api/exports/{export_id}/download",
    }


@router.post("/projects/{project_id}/export/pdf")
def create_pdf_export(project_id: str, req: Optional[ExportRequest] = None) -> Dict[str, Any]:
    """Shortcut endpoint for requesting PDF exports."""
    request_data = req or ExportRequest(format="pdf")
    request_data.format = "pdf"
    return create_export_job(project_id, request_data)


@router.post("/projects/{project_id}/export/data")
def create_data_export(project_id: str, req: Optional[ExportRequest] = None) -> Dict[str, Any]:
    """Shortcut endpoint for requesting raw CSV data extracts."""
    request_data = req or ExportRequest(format="csv")
    request_data.format = "csv"
    return create_export_job(project_id, request_data)


@router.get("/exports/{export_id}/status")
def get_export_status(export_id: str) -> Dict[str, Any]:
    """Retrieve async export job status, progress, and snapshot metadata."""
    status_info = default_export_engine.get_job_status(export_id)
    if not status_info:
        raise HTTPException(status_code=404, detail=f"Export job '{export_id}' not found")
    return status_info


@router.get("/exports/{export_id}/download")
def download_export_artifact(export_id: str):
    """Download the generated export artifact file."""
    status_info = default_export_engine.get_job_status(export_id)
    if not status_info:
        raise HTTPException(status_code=404, detail=f"Export job '{export_id}' not found")

    if status_info.get("status") != "completed":
        raise HTTPException(status_code=400, detail=f"Export job '{export_id}' is not completed yet (status: {status_info.get('status')})")

    file_path = status_info.get("file_path")
    if not file_path or not Path(file_path).exists():
        raise HTTPException(status_code=404, detail=f"Artifact file for export '{export_id}' not found on disk")

    p = Path(file_path)
    media_types = {
        ".html": "text/html",
        ".md": "text/markdown",
        ".csv": "text/csv",
        ".pdf": "application/pdf",
        ".json": "application/json",
    }
    media_type = media_types.get(p.suffix.lower(), "application/octet-stream")
    return FileResponse(path=str(p), filename=p.name, media_type=media_type)
