"""FastAPI router for Semantic Model & Relationships in PyBI v1 REST API."""

import os
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from pybi.core.semantic_model import (
    SemanticModel,
    SemanticTable,
    SemanticRelationship,
    autodetect_relationships,
)
from pybi.core.storage import default_storage

router = APIRouter(prefix="/api/v1/projects/{project_id}/semantic", tags=["Semantic Model"])


def get_semantic_model_path(project_id: str) -> str:
    """Get file path to semantic_model.yaml for given project."""
    data_dir = default_storage.get_project_data_dir(project_id)
    return os.path.join(data_dir, "semantic_model.yaml")


def load_project_semantic_model(project_id: str) -> SemanticModel:
    """Load semantic model for project or return default empty model."""
    filepath = get_semantic_model_path(project_id)
    if os.path.exists(filepath):
        try:
            return SemanticModel.load_yaml_file(filepath)
        except Exception:
            pass
    return SemanticModel(name=f"{project_id}_semantic_model", tables=[], relationships=[], rls_rules=[])


def save_project_semantic_model(project_id: str, model: SemanticModel) -> str:
    """Save semantic model to project storage directory."""
    filepath = get_semantic_model_path(project_id)
    model.save_yaml_file(filepath)
    return filepath


class UpdateRelationshipsRequest(BaseModel):
    """Payload for updating model relationships."""

    relationships: List[SemanticRelationship]


@router.get("", response_model=Dict[str, Any])
def get_semantic_model(project_id: str):
    """Get complete semantic model definition for project."""
    model = load_project_semantic_model(project_id)
    return model.to_dict()


@router.get("/tables", response_model=List[Dict[str, Any]])
def get_semantic_tables(project_id: str):
    """Get tables metadata and column schema for dropdown population."""
    model = load_project_semantic_model(project_id)
    return [t.model_dump(mode="json") for t in model.tables]


@router.put("/relationships", response_model=Dict[str, Any])
def update_relationships(project_id: str, payload: UpdateRelationshipsRequest):
    """Save updated relationships list for project."""
    model = load_project_semantic_model(project_id)
    model.relationships = payload.relationships
    save_project_semantic_model(project_id, model)
    return {"message": "Relationships updated successfully", "relationships": [r.model_dump(mode="json") for r in model.relationships]}


@router.post("/autodetect", response_model=List[Dict[str, Any]])
def autodetect_model_relationships(project_id: str):
    """Autodetect relationships between project tables."""
    model = load_project_semantic_model(project_id)
    new_rels = autodetect_relationships(model.tables, model.relationships)
    return [r.model_dump(mode="json") for r in new_rels]
