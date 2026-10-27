"""FastAPI router for ETL Pipeline operations in PyBI v1 REST API."""

from typing import Any, Dict, Optional, Union
import uuid

from fastapi import APIRouter, HTTPException, status

from pybi.api.schemas import DagSaveRequest, JobStatusResponse
from pybi.api.v1.models import (
    ETLDAGSchema,
    ETLExecuteRequest,
    ETLExecuteResponse,
    ETLPreviewRequest,
    ETLPreviewResponse,
    MessageResponse,
    SaveETLDAGRequest,
)
from pybi.core.storage import default_storage
from pybi.dashboard.binding import default_binder
from pybi.etl.executor import ETLExecutor
import pybi.storage.project_manager as pm

router = APIRouter(prefix="/api/v1/projects/{project_id}/etl", tags=["ETL"])

# In-memory store for ETL execution job statuses
_jobs: Dict[str, JobStatusResponse] = {}


@router.get("", response_model=ETLDAGSchema)
@router.get("/dag", response_model=ETLDAGSchema)
@router.get("/query", response_model=ETLDAGSchema)
def get_etl_dag(project_id: str) -> ETLDAGSchema:
    """Fetch saved ETL DAG or linear query configuration for project."""
    if not default_storage.project_exists(project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found")
    dag_dict = pm.load_dag(project_id)
    return ETLDAGSchema(
        nodes=dag_dict.get("nodes", []),
        edges=dag_dict.get("edges", []),
        query_name=dag_dict.get("query_name"),
        source=dag_dict.get("source", {}),
        steps=dag_dict.get("steps", []),
    )


@router.put("", response_model=MessageResponse)
@router.put("/dag", response_model=MessageResponse)
@router.put("/query", response_model=MessageResponse)
def save_etl_dag(
    project_id: str,
    req: Union[SaveETLDAGRequest, DagSaveRequest, Dict[str, Any]],
) -> MessageResponse:
    """Save or update ETL DAG or linear query configuration for project."""
    if not default_storage.project_exists(project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found")

    if isinstance(req, SaveETLDAGRequest):
        if req.query:
            dag_dict = req.query.model_dump()
        elif req.dag:
            dag_dict = req.dag.model_dump()
        else:
            dag_dict = {}
    elif isinstance(req, DagSaveRequest):
        dag_dict = req.model_dump()
    elif isinstance(req, dict) and "query" in req:
        dag_dict = req["query"]
    elif isinstance(req, dict) and "dag" in req:
        dag_dict = req["dag"]
    elif isinstance(req, dict):
        dag_dict = req
    else:
        dag_dict = {"nodes": [], "edges": []}

    pm.save_dag(project_id, dag_dict)
    return MessageResponse(
        message=f"ETL configuration saved successfully for project '{project_id}'",
        success=True,
    )


@router.post("/execute", response_model=ETLExecuteResponse)
def execute_etl_pipeline(
    project_id: str,
    req: Optional[ETLExecuteRequest] = None,
) -> ETLExecuteResponse:
    """Execute ETL pipeline DAG or linear query for project using Polars and DuckDB."""
    if req and req.query:
        dag_dict = req.query.model_dump()
    elif req and req.dag and (req.dag.nodes or req.dag.steps or req.dag.source):
        dag_dict = req.dag.model_dump()
    elif default_storage.project_exists(project_id):
        dag_dict = pm.load_dag(project_id)
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found")

    data_dir = default_storage.get_project_data_dir(project_id)
    executor = ETLExecutor(duckdb_conn=default_binder.duckdb_conn, base_dir=data_dir)
    result = executor.execute(dag_dict)

    job_id = f"job_{uuid.uuid4().hex[:8]}"
    out_tables = list(result.output_tables.keys())

    # Register output dataframes into default_binder for dashboard widgets
    for tbl_name, df in result.output_tables.items():
        default_binder.register_source(tbl_name, df)

    status_str = "success" if result.status == "success" else "error"
    job_resp = JobStatusResponse(
        job_id=job_id,
        status=status_str,
        logs=result.logs,
        output_tables=out_tables,
        error=result.error if status_str == "error" else None,
    )
    _jobs[job_id] = job_resp

    return ETLExecuteResponse(
        status=status_str,
        logs=result.logs,
        output_tables=out_tables,
        error=result.error or None,
    )


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(project_id: str, job_id: str) -> JobStatusResponse:
    """Check job execution status by job_id."""
    if job_id not in _jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ETL Job '{job_id}' not found",
        )
    return _jobs[job_id]


@router.post("/preview", response_model=ETLPreviewResponse)
def preview_node_output(project_id: str, req: ETLPreviewRequest) -> ETLPreviewResponse:
    """Execute ETL pipeline up to specified node or step_index and preview dataframe results."""
    if not default_storage.project_exists(project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found")

    if req.query:
        dag_dict = req.query.model_dump()
    else:
        dag_dict = pm.load_dag(project_id)

    data_dir = default_storage.get_project_data_dir(project_id)
    executor = ETLExecutor(duckdb_conn=default_binder.duckdb_conn, base_dir=data_dir)

    df = None
    if req.step_index is not None:
        result = executor.execute_linear_etl(dag_dict, stop_at_step_index=req.step_index)
        step_key = f"step_{req.step_index}"
        if step_key in result.dataframes:
            df = result.dataframes[step_key]
        elif "source" in result.dataframes and req.step_index == 0:
            df = result.dataframes["source"]
        elif result.output_tables:
            df = list(result.output_tables.values())[0]
    else:
        result = executor.execute(dag_dict)
        node_key = req.node_id or ""
        if node_key in result.dataframes:
            df = result.dataframes[node_key]
        elif result.dataframes:
            df = list(result.dataframes.values())[-1]

    if df is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Specified node or step_index produced no dataframe output during execution",
        )

    preview_df = df.head(req.limit)
    rows = preview_df.to_dicts()
    cols = preview_df.columns

    return ETLPreviewResponse(
        node_id=req.node_id,
        step_index=req.step_index,
        columns=cols,
        rows=rows,
        total_rows=len(df),
    )
