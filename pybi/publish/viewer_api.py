"""Lightweight FastAPI router for read-only viewer consumption."""

from fastapi import APIRouter, HTTPException
from typing import Any, Dict

router = APIRouter(prefix="/api/viewer", tags=["viewer"])


@router.get("/health")
def viewer_health() -> Dict[str, str]:
    """Health check endpoint for viewer API."""
    return {"status": "ok", "service": "pybi-viewer-api"}


@router.get("/projects/{project_id}")
def get_published_project(project_id: str) -> Dict[str, Any]:
    """Fetch published dashboard layout and schema for read-only viewing."""
    return {
        "project_id": project_id,
        "status": "published",
        "widgets": [],
        "tables": []
    }
