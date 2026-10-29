"""FastAPI router for ETL Pipeline operations in PyBI v1 REST API."""

import time
from typing import Any, Dict, Optional, Union
import uuid

from fastapi import APIRouter, HTTPException, status

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
from pybi.schemas.etl import ETLQuery
import pybi.storage.project_manager as pm

router = APIRouter(prefix="/api/v1/projects/{project_id}/etl", tags=["ETL"])

# In-memory store for ETL execution job statuses
_jobs: Dict[str, JobStatusResponse] = {}


@router.get("", response_model=Union[ETLDAGSchema, Dict[str, Any]])
@router.get("/dag", response_model=Union[ETLDAGSchema, Dict[str, Any]])
@router.get("/query")
async def get_etl_query(project_id: str):
    """Retrieve saved ETL query or DAG configuration for project."""
    if not default_storage.project_exists(project_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )
    query_config = ETLEngine.load_query(project_id)
    if not query_config:
        return {"query_name": "default", "source": {}, "steps": [], "nodes": [], "edges": []}
    return query_config


@router.put("", response_model=Dict[str, Any])
@router.put("/dag", response_model=Dict[str, Any])
@router.put("/query")
async def save_etl_query(
    project_id: str,
    req: Union[SaveETLDAGRequest, DagSaveRequest, ETLQuery, Dict[str, Any]],
):
    """Save or update ETL query linear configuration or DAG sequence."""
    if not default_storage.project_exists(project_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )

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
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Impossibile salvare la query ETL",
        )

    return {
        "status": "success",
        "message": "Query ETL salvata con successo",
        "success": True,
    }


@router.post("/preview")
async def preview_etl_step(project_id: str, payload: Union[ETLPreviewRequest, Dict[str, Any]]):
    """Generate intermediate preview data up to step_index with 1,000 row limit."""
    start_time = time.time()
    try:
        if hasattr(payload, "query") and payload.query:
            query = payload.query
        elif isinstance(payload, dict) and "query" in payload and payload["query"]:
            query = payload["query"]
        else:
            query = ETLEngine.load_query(project_id) or {"query_name": "default", "source": {}, "steps": []}

        step_idx = getattr(payload, "step_index", None)
        if step_idx is None and isinstance(payload, dict):
            step_idx = payload.get("step_index")

        limit_val = getattr(payload, "limit", 1000)
        if limit_val is None or (isinstance(payload, dict) and "limit" in payload and payload["limit"]):
            limit_val = payload["limit"] if isinstance(payload, dict) else limit_val
        if limit_val is None or limit_val <= 0:
            limit_val = 1000

        node_id = getattr(payload, "node_id", None) or (payload.get("node_id") if isinstance(payload, dict) else None)

        df_preview = ETLEngine.generate_preview(
            project_id=project_id,
            query=query,
            step_index=step_idx,
            limit=limit_val,
        )
        elapsed = round(time.time() - start_time, 3)

        cols = list(df_preview.columns)
        dtypes = {col: str(dtype) for col, dtype in zip(df_preview.columns, df_preview.dtypes)}
        rows = df_preview.to_dict(orient="records")

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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Errore nella generazione dell'anteprima: {str(e)}",
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
