"""FastAPI router for UI Schema endpoint in PyBI v1 REST API."""

from typing import Optional
from fastapi import APIRouter
from pybi.server.ui_schema import UISchema, get_page_ui_schema as get_schema

router = APIRouter(prefix="/api/v1/ui", tags=["UI Schema"])


@router.get("/schema/{page_name}", response_model=UISchema)
def get_page_ui_schema(page_name: str, project_id: Optional[str] = None) -> UISchema:
    """Get dynamic page UI Schema JSON representation."""
    return get_schema(page_name, project_id=project_id)
