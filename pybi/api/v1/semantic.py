"""FastAPI router for Semantic Model & Relationships in PyBI v1 REST API."""

import os
from typing import Any, Dict, List, Optional
import duckdb
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from pybi.core.model_sync import (
    get_semantic_model_path,
    load_project_semantic_model,
    save_project_semantic_model,
    sync_etl_outputs_into_model,
)
from pybi.core.semantic_model import (
    SemanticModel,
    SemanticTable,
    SemanticRelationship,
    autodetect_relationships,
)
from pybi.core.storage import default_storage
from pybi.dashboard.binding import default_binder

router = APIRouter(prefix="/api/v1/projects/{project_id}/semantic", tags=["Semantic Model"])


class UpdateRelationshipsRequest(BaseModel):
    """Payload for updating model relationships."""

    relationships: List[SemanticRelationship]


class ParameterValuesRequest(BaseModel):
    """Payload for requesting cascading parameter values."""

    table_name: str
    column_name: str
    parent_filters: Optional[Dict[str, Any]] = None


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


@router.post("/parameters")
def get_semantic_parameter_options(project_id: str, payload: ParameterValuesRequest):
    """Fetch distinct parameter option values filtered by parent parameters."""
    tbl_name = payload.table_name
    col_name = payload.column_name

    if tbl_name not in default_binder.list_sources():
        return {"project_id": project_id, "table_name": tbl_name, "column_name": col_name, "options": []}

    df = default_binder.get_source_data(tbl_name)
    con = duckdb.connect(":memory:")
    raw_df = df.to_pandas() if hasattr(df, "to_pandas") else df
    con.register("tbl", raw_df)

    where_clauses = [f"\"{col_name}\" IS NOT NULL"]
    if payload.parent_filters:
        for p_col, p_val in payload.parent_filters.items():
            if isinstance(p_val, list) and p_val:
                vals = ", ".join(f"'{v}'" for v in p_val)
                where_clauses.append(f"\"{p_col}\" IN ({vals})")
            elif p_val is not None and str(p_val).strip() != "":
                where_clauses.append(f"\"{p_col}\" = '{p_val}'")

    where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    sql = f"SELECT DISTINCT \"{col_name}\" FROM tbl {where_str} ORDER BY \"{col_name}\""

    try:
        res = con.execute(sql).fetchall()
        opts = [str(r[0]) for r in res if r[0] is not None]
        return {
            "project_id": project_id,
            "table_name": tbl_name,
            "column_name": col_name,
            "options": opts,
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Parameter options fetch failed: {e}")
