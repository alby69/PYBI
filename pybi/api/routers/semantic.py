"""REST API Router for Semantic Model View in PyBI."""

import json
import os
from typing import List, Dict, Any, Optional
import duckdb
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from pybi.models.semantic import (
    SemanticModel,
    TableMetadata,
    ColumnMetadata,
    Relationship,
    Measure,
    Hierarchy,
    HierarchyLevel,
    CardinalityType,
    CrossFilterDirection,
    JoinType,
)
from pybi.core.autodetect_relationships import autodetect_model_relationships
from pybi.core.semantic_model import (
    SemanticModel as CoreSemanticModel,
    SemanticTable as CoreSemanticTable,
    SemanticColumn as CoreSemanticColumn,
    SemanticMeasure as CoreSemanticMeasure,
    SemanticRelationship as CoreSemanticRelationship,
    Cardinality as CoreCardinality,
    JoinType as CoreJoinType,
)
from pybi.core.model_sync import (
    load_project_semantic_model as core_load_project_semantic_model,
    save_project_semantic_model as core_save_project_semantic_model,
)
from pybi.core.storage import default_storage
from pybi.dashboard.binding import default_binder

router = APIRouter(prefix="/api/v1/projects/{project_id}/semantic", tags=["Semantic Model View"])


class UpdateRelationshipsRequest(BaseModel):
    """Payload for updating model relationships list."""

    relationships: List[Relationship]


class ParameterValuesRequest(BaseModel):
    """Payload for requesting cascading parameter values."""

    table_name: str
    column_name: str
    parent_filters: Optional[Dict[str, Any]] = None


def _get_view_model_json_path(project_id: str) -> str:
    """Get path to semantic_model.json for a given project."""
    data_dir = default_storage.get_project_data_dir(project_id)
    return os.path.join(data_dir, "semantic_model.json")


def load_semantic_model_by_id(project_id: str) -> SemanticModel:
    """Load semantic model for project (merging core model definition and view metadata)."""
    json_path = _get_view_model_json_path(project_id)

    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["project_id"] = project_id
            if not data.get("name"):
                data["name"] = f"{project_id}_semantic_model"
            return SemanticModel.model_validate(data)
        except Exception:
            pass

    # Fallback/Initialize from core model
    core_model = core_load_project_semantic_model(project_id)

    tables: List[TableMetadata] = []
    x_pos, y_pos = 50.0, 50.0

    for idx, ct in enumerate(core_model.tables):
        cols = [
            ColumnMetadata(
                name=cc.name,
                data_type=cc.data_type,
                is_key=cc.is_key,
                is_hidden=cc.is_hidden,
            )
            for cc in ct.columns
        ]

        meas = [
            Measure(
                id=f"meas_{ct.name}_{cm.name}".lower(),
                name=cm.name,
                table_name=ct.name,
                expression=cm.expression or f"{cm.agg_func or 'SUM'}({cm.column_name or cm.name})",
                format_string=cm.format_string or "€ #,##0.00",
            )
            for cm in ct.measures
        ]

        tables.append(
            TableMetadata(
                name=ct.name,
                position_x=x_pos + (idx % 3) * 320,
                position_y=y_pos + (idx // 3) * 350,
                columns=cols,
                measures=meas,
            )
        )

    relationships: List[Relationship] = []
    for idx, cr in enumerate(core_model.relationships):
        rel_id = f"rel_{cr.from_table}_{cr.from_column}_{cr.to_table}_{cr.to_column}_{idx}".lower()

        card_str = cr.cardinality.value if hasattr(cr.cardinality, "value") else str(cr.cardinality)
        card_enum = CardinalityType.MANY_TO_ONE
        for c_enum in CardinalityType:
            if c_enum.value == card_str:
                card_enum = c_enum
                break

        join_str = cr.join_type.value if hasattr(cr.join_type, "value") else str(cr.join_type)
        join_enum = JoinType.LEFT
        for j_enum in JoinType:
            if j_enum.value == join_str:
                join_enum = j_enum
                break

        relationships.append(
            Relationship(
                id=rel_id,
                from_table=cr.from_table,
                from_column=cr.from_column,
                to_table=cr.to_table,
                to_column=cr.to_column,
                cardinality=card_enum,
                cross_filter_direction=CrossFilterDirection.SINGLE,
                join_type=join_enum,
                is_active=getattr(cr, "is_active", True),
            )
        )

    all_measures = []
    for t in tables:
        all_measures.extend(t.measures)

    model = SemanticModel(
        project_id=project_id,
        name=core_model.name or f"{project_id}_semantic_model",
        tables=tables,
        relationships=relationships,
        measures=all_measures,
        hierarchies=[],
    )

    save_semantic_model(project_id, model)
    return model


def save_semantic_model(project_id: str, model: SemanticModel) -> None:
    """Save semantic model to project storage and sync core semantic model."""
    json_path = _get_view_model_json_path(project_id)
    os.makedirs(os.path.dirname(json_path), exist_ok=True)

    if not model.name:
        model.name = f"{project_id}_semantic_model"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(model.model_dump(mode="json"), f, indent=2)

    # Convert to CoreSemanticModel and sync
    core_tables: List[CoreSemanticTable] = []
    for tm in model.tables:
        core_cols = [
            CoreSemanticColumn(
                name=cm.name,
                column_name=cm.name,
                data_type=cm.data_type,
                is_key=cm.is_key,
                is_hidden=cm.is_hidden,
            )
            for cm in tm.columns
        ]

        table_measures = [m for m in model.measures if m.table_name == tm.name]
        for m in tm.measures:
            if not any(tm_m.id == m.id for tm_m in table_measures):
                table_measures.append(m)

        core_meas = [
            CoreSemanticMeasure(
                name=m.name,
                expression=m.expression,
                format_string=m.format_string,
                label=m.name,
            )
            for m in table_measures
        ]

        core_tables.append(
            CoreSemanticTable(
                name=tm.name,
                source_table=tm.name,
                columns=core_cols,
                measures=core_meas,
            )
        )

    core_rels: List[CoreSemanticRelationship] = []
    for r in model.relationships:
        card_val = r.cardinality.value if hasattr(r.cardinality, "value") else str(r.cardinality)
        join_val = r.join_type.value if hasattr(r.join_type, "value") else str(r.join_type)

        core_rels.append(
            CoreSemanticRelationship(
                from_table=r.from_table,
                from_column=r.from_column,
                to_table=r.to_table,
                to_column=r.to_column,
                cardinality=card_val,
                join_type=join_val,
                is_active=r.is_active,
            )
        )

    core_model = CoreSemanticModel(
        name=model.name,
        tables=core_tables,
        relationships=core_rels,
    )
    core_save_project_semantic_model(project_id, core_model)


def add_or_update_relationship(project_id: str, rel: Relationship) -> Relationship:
    """Add or update a relationship in the model."""
    model = load_semantic_model_by_id(project_id)
    idx = next((i for i, r in enumerate(model.relationships) if r.id == rel.id), -1)
    if idx >= 0:
        model.relationships[idx] = rel
    else:
        pair_idx = next(
            (
                i
                for i, r in enumerate(model.relationships)
                if r.from_table == rel.from_table
                and r.from_column == rel.from_column
                and r.to_table == rel.to_table
                and r.to_column == rel.to_column
            ),
            -1,
        )
        if pair_idx >= 0:
            model.relationships[pair_idx] = rel
        else:
            model.relationships.append(rel)

    save_semantic_model(project_id, model)
    return rel


def remove_relationship(project_id: str, rel_id: str) -> None:
    """Remove a relationship by ID."""
    model = load_semantic_model_by_id(project_id)
    model.relationships = [r for r in model.relationships if r.id != rel_id]
    save_semantic_model(project_id, model)


def upsert_measure(project_id: str, measure: Measure) -> Measure:
    """Upsert a calculated measure in the model."""
    model = load_semantic_model_by_id(project_id)

    idx = next((i for i, m in enumerate(model.measures) if m.id == measure.id or (m.name == measure.name and m.table_name == measure.table_name)), -1)
    if idx >= 0:
        model.measures[idx] = measure
    else:
        model.measures.append(measure)

    for tbl in model.tables:
        if tbl.name == measure.table_name:
            t_idx = next((i for i, m in enumerate(tbl.measures) if m.id == measure.id or m.name == measure.name), -1)
            if t_idx >= 0:
                tbl.measures[t_idx] = measure
            else:
                tbl.measures.append(measure)

    save_semantic_model(project_id, model)
    return measure


@router.get("", response_model=SemanticModel)
async def get_semantic_model(project_id: str):
    """Restituisce l'intero modello semantico (tabelle, relazioni, misure, gerarchie e posizioni canvas)."""
    return load_semantic_model_by_id(project_id)


@router.put("", response_model=SemanticModel)
async def update_semantic_model(project_id: str, model: SemanticModel):
    """Salva l'intero modello semantico incluse le posizioni dei nodi nel canvas."""
    save_semantic_model(project_id, model)
    return model


@router.get("/tables", response_model=List[Dict[str, Any]])
async def get_semantic_tables(project_id: str):
    """Get tables metadata and column schema."""
    model = load_semantic_model_by_id(project_id)
    return [t.model_dump(mode="json") for t in model.tables]


@router.post("/relationships", response_model=Relationship)
async def create_relationship(project_id: str, rel: Relationship):
    """Aggiunge o aggiorna una relazione fra tabelle."""
    return add_or_update_relationship(project_id, rel)


@router.put("/relationships", response_model=Dict[str, Any])
async def update_relationships(project_id: str, payload: UpdateRelationshipsRequest):
    """Aggiorna l'intero elenco delle relazioni del modello."""
    model = load_semantic_model_by_id(project_id)
    model.relationships = payload.relationships
    save_semantic_model(project_id, model)
    return {"message": "Relationships updated successfully", "relationships": [r.model_dump(mode="json") for r in model.relationships]}


@router.delete("/relationships/{rel_id}")
async def delete_relationship(project_id: str, rel_id: str):
    """Rimuove una relazione dal modello."""
    remove_relationship(project_id, rel_id)
    return {"status": "success", "deleted_id": rel_id}


@router.post("/relationships/autodetect", response_model=List[Relationship])
@router.post("/autodetect", response_model=List[Relationship])
async def autodetect_relationships_endpoint(project_id: str):
    """Analizza le tabelle del modello e propone automaticamente le relazioni valide."""
    model = load_semantic_model_by_id(project_id)
    detected_rels = autodetect_model_relationships(model.tables, model.relationships)
    return detected_rels


@router.post("/measures", response_model=Measure)
async def save_measure(project_id: str, measure: Measure):
    """Crea o aggiorna una misura calcolata."""
    return upsert_measure(project_id, measure)


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
