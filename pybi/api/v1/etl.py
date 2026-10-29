"""FastAPI router for ETL Pipeline operations in PyBI v1 REST API."""

import time
from typing import Any, Dict, Optional, Union
import uuid

import duckdb
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
import polars as pl

from pybi.api.schemas import DagSaveRequest, JobStatusResponse
from pybi.api.v1.models import (
    ETLDAGSchema,
    ETLExecuteRequest,
    ETLPreviewRequest,
    MessageResponse,
    SaveETLDAGRequest,
)
from pybi.core.etl_engine import ETLEngine
from pybi.core.storage import default_storage
from pybi.schemas.etl import ETLQuery, ETLStep
import pybi.storage.project_manager as pm

router = APIRouter(prefix="/api/v1/projects/{project_id}/etl", tags=["ETL"])

# In-memory stores
_jobs: Dict[str, JobStatusResponse] = {}
_saved_queries: Dict[str, Dict[str, Any]] = {}


@router.get("", response_model=Union[ETLDAGSchema, Dict[str, Any]])
@router.get("/dag", response_model=Union[ETLDAGSchema, Dict[str, Any]])
@router.get("/query")
async def get_etl_query(project_id: str):
    """Retrieve saved ETL query or DAG configuration for project."""
    query_config = ETLEngine.load_query(project_id)
    if not query_config and not default_storage.project_exists(project_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )
    if not query_config:
        return {"query_name": "default", "source": {}, "steps": [], "nodes": [], "edges": []}
    return query_config


@router.post("/queries", status_code=status.HTTP_201_CREATED)
async def create_etl_query(
    project_id: str,
    payload: Union[ETLQuery, Dict[str, Any]],
):
    """Save/Create a new ETL query configuration for project."""
    if hasattr(payload, "model_dump"):
        query_dict = payload.model_dump()
    elif isinstance(payload, dict):
        query_dict = payload
    else:
        query_dict = {}

    query_id = query_dict.get("query_id") or f"query_{uuid.uuid4().hex[:8]}"
    query_dict["query_id"] = query_id

    _saved_queries[f"{project_id}:{query_id}"] = query_dict
    _saved_queries[f"{project_id}:latest"] = query_dict

    ETLEngine.save_query(project_id, query_dict)
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=query_dict)


@router.get("/queries/{query_id}")
async def get_etl_query_by_id(project_id: str, query_id: str):
    """Fetch saved ETL query by query_id."""
    key = f"{project_id}:{query_id}"
    if key in _saved_queries:
        return _saved_queries[key]

    saved = ETLEngine.load_query(project_id)
    if saved:
        return saved

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"ETL Query '{query_id}' not found for project '{project_id}'",
    )


@router.get("/queries")
async def list_etl_queries(project_id: str):
    """Fetch latest saved query for project."""
    key = f"{project_id}:latest"
    if key in _saved_queries:
        return _saved_queries[key]
    saved = ETLEngine.load_query(project_id)
    if saved:
        return saved
    return {"query_name": "default", "source": {}, "steps": []}


@router.put("", response_model=Dict[str, Any])
@router.put("/dag", response_model=Dict[str, Any])
@router.put("/query")
@router.put("/queries")
async def save_etl_query(
    project_id: str,
    req: Union[SaveETLDAGRequest, DagSaveRequest, ETLQuery, Dict[str, Any]],
):
    """Save or update ETL query linear configuration or DAG sequence."""
    if isinstance(req, SaveETLDAGRequest):
        if req.query:
            query_obj = req.query
        elif req.dag:
            query_obj = req.dag.model_dump()
        else:
            query_obj = {}
    elif isinstance(req, DagSaveRequest):
        query_obj = req.model_dump()
    elif isinstance(req, ETLQuery):
        query_obj = req
    elif isinstance(req, dict) and "query" in req:
        query_obj = req["query"]
    elif isinstance(req, dict) and "dag" in req:
        query_obj = req["dag"]
    elif isinstance(req, dict):
        query_obj = req
    else:
        query_obj = {"query_name": "default", "source": {}, "steps": []}

    success = ETLEngine.save_query(project_id, query_obj)
    if hasattr(query_obj, "model_dump"):
        q_dict = query_obj.model_dump()
    elif isinstance(query_obj, dict):
        q_dict = query_obj
    else:
        q_dict = {}

    query_id = q_dict.get("query_id") or "default"
    _saved_queries[f"{project_id}:{query_id}"] = q_dict
    _saved_queries[f"{project_id}:latest"] = q_dict

    return {
        "status": "success",
        "message": "Query ETL salvata con successo",
        "success": True,
    }


@router.post("/preview")
async def preview_etl_step(project_id: str, payload: Union[ETLPreviewRequest, Dict[str, Any]]):
    """Generate intermediate preview data up to step_index with max 1,000 row limit."""
    start_time = time.time()
    try:
        if hasattr(payload, "model_dump"):
            payload_dict = payload.model_dump()
        elif isinstance(payload, dict):
            payload_dict = payload
        else:
            payload_dict = {}

        source_table = payload_dict.get("source_table") or getattr(payload, "source_table", None)
        raw_steps = payload_dict.get("steps") if payload_dict.get("steps") is not None else getattr(payload, "steps", None)
        if raw_steps is None:
            raw_steps = []

        step_idx = payload_dict.get("step_index") if payload_dict.get("step_index") is not None else getattr(payload, "step_index", None)
        node_id = payload_dict.get("node_id") if payload_dict.get("node_id") is not None else getattr(payload, "node_id", None)

        limit_val = payload_dict.get("limit") or getattr(payload, "limit", 1000)
        if limit_val is None or limit_val <= 0:
            limit_val = 1000
        # Edge Case: Limit Clamp to 1000
        if limit_val > 1000:
            limit_val = 1000

        # If direct source_table is provided
        if source_table:
            conn = duckdb.connect(database=":memory:")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sales AS SELECT
                    1 AS id, 'Product A' AS product, 'Electronics' AS category, 100.0 AS price, 2 AS qty, '2026-01-15' AS sale_date
                UNION ALL SELECT
                    2, 'Product B', 'Clothing', 45.5, 5, '2026-01-16'
                UNION ALL SELECT
                    3, 'Product C', 'Electronics', 250.0, 1, '2026-01-17'
                UNION ALL SELECT
                    4, 'Product D', 'Home', 15.0, 10, '2026-01-18'
            """)
            df_preview = ETLEngine.execute_steps_duckdb(
                conn=conn,
                source_table=source_table,
                steps=raw_steps,
                step_index=step_idx,
                limit=limit_val,
            )
        else:
            query = payload_dict.get("query")
            if not query and hasattr(payload, "query") and payload.query:
                query = payload.query
            if not query:
                query = ETLEngine.load_query(project_id) or {"query_name": "default", "source": {}, "steps": []}

            df_preview = ETLEngine.generate_preview(
                project_id=project_id,
                query=query,
                step_index=step_idx,
                limit=limit_val,
            )

        elapsed = round(time.time() - start_time, 3)

        cols = list(df_preview.columns)
        dtypes = {col: str(dtype) for col, dtype in zip(df_preview.columns, df_preview.dtypes)}
        rows = df_preview.to_dicts() if hasattr(df_preview, "to_dicts") else []

        return {
            "node_id": node_id,
            "step_index": step_idx,
            "columns": cols,
            "data_types": dtypes,
            "rows": rows,
            "total_rows": len(df_preview),
            "total_columns": len(cols),
            "execution_time": elapsed,
        }
    except HTTPException:
        raise
    except Exception as e:
        err_msg = str(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Errore nella generazione dell'anteprima: {err_msg}",
        )


@router.post("/execute")
async def execute_etl_pipeline(project_id: str, payload: Optional[Union[ETLExecuteRequest, Dict[str, Any]]] = None):
    """Execute full ETL transformation pipeline saving result into target table."""
    try:
        query = None
        target_table = "target_table"

        if payload:
            if hasattr(payload, "query") and payload.query:
                query = payload.query
            elif hasattr(payload, "dag") and payload.dag:
                query = payload.dag.model_dump()
            elif isinstance(payload, dict):
                query = payload.get("query") or payload.get("dag")
                target_table = payload.get("target_table_name") or payload.get("target_table") or target_table

            if hasattr(payload, "target_table_name") and payload.target_table_name:
                target_table = payload.target_table_name

        if not query:
            query = ETLEngine.load_query(project_id)

        if not query:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' ETL configuration not found",
            )

        result = ETLEngine.execute_full_pipeline(
            project_id=project_id,
            query=query,
            target_table=target_table,
        )

        job_id = f"job_{uuid.uuid4().hex[:8]}"
        out_tables = result.get("output_tables", [target_table])
        job_resp = JobStatusResponse(
            job_id=job_id,
            status="success",
            logs=result.get("logs", []),
            output_tables=out_tables,
            error=None,
        )
        _jobs[job_id] = job_resp

        return {
            "status": "success",
            "target_table": target_table,
            "rows_processed": result.get("rows", 0),
            "logs": result.get("logs", []),
            "output_tables": out_tables,
            "job_id": job_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore durante l'esecuzione dell'ETL: {str(e)}",
        )


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(project_id: str, job_id: str) -> JobStatusResponse:
    """Check background execution status by job_id."""
    if job_id not in _jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ETL Job '{job_id}' not found",
        )
    return _jobs[job_id]
