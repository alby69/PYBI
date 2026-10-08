"""FastAPI router for ETL Pipeline operations in PyBI v1 REST API."""

from fastapi import APIRouter, HTTPException, status
from typing import Any, Dict, Optional

from pybi.core.storage import default_storage
from pybi.etl.executor import ETLExecutor
from pybi.api.v1.models import (
    ETLDAGSchema,
    ETLExecuteRequest,
    ETLExecuteResponse,
    ETLPreviewRequest,
    ETLPreviewResponse,
    MessageResponse,
    SaveETLDAGRequest,
)

router = APIRouter(prefix="/api/v1/projects/{project_id}/etl", tags=["ETL"])


@router.get("", response_model=ETLDAGSchema)
def get_etl_dag(project_id: str) -> ETLDAGSchema:
    """Fetch saved ETL DAG for project."""
    if not default_storage.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
    dag_dict = default_storage.load_etl_dag(project_id)
    return ETLDAGSchema(
        nodes=dag_dict.get("nodes", []),
        edges=dag_dict.get("edges", []),
    )


@router.put("", response_model=MessageResponse)
def save_etl_dag(project_id: str, req: SaveETLDAGRequest) -> MessageResponse:
    """Save or update ETL DAG configuration for project."""
    dag_dict = req.dag.model_dump()
    default_storage.save_etl_dag(project_id, dag_dict)
    return MessageResponse(
        message=f"ETL DAG saved successfully for project '{project_id}'",
        success=True,
    )


@router.post("/execute", response_model=ETLExecuteResponse)
def execute_etl_pipeline(project_id: str, req: Optional[ETLExecuteRequest] = None) -> ETLExecuteResponse:
    """Execute ETL pipeline DAG for project using Polars and DuckDB."""
    if req and req.dag and req.dag.nodes:
        dag_dict = req.dag.model_dump()
    elif default_storage.project_exists(project_id):
        dag_dict = default_storage.load_etl_dag(project_id)
    else:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

    data_dir = default_storage.get_project_data_dir(project_id)
    executor = ETLExecutor(base_dir=data_dir)
    result = executor.execute(dag_dict)

    if result.status == "error":
        return ETLExecuteResponse(
            status="error",
            logs=result.logs,
            output_tables=list(result.output_tables.keys()),
            error=result.error or "Pipeline execution failed",
        )

    return ETLExecuteResponse(
        status="success",
        logs=result.logs,
        output_tables=list(result.output_tables.keys()),
    )


@router.post("/preview", response_model=ETLPreviewResponse)
def preview_node_output(project_id: str, req: ETLPreviewRequest) -> ETLPreviewResponse:
    """Execute ETL pipeline up to specified node and preview dataframe results."""
    if not default_storage.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

    dag_dict = default_storage.load_etl_dag(project_id)
    data_dir = default_storage.get_project_data_dir(project_id)
    executor = ETLExecutor(base_dir=data_dir)
    result = executor.execute(dag_dict)

    node_id = req.node_id
    if node_id not in result.dataframes:
        raise HTTPException(
            status_code=400,
            detail=f"Node '{node_id}' not found or produced no dataframe output during execution",
        )

    df = result.dataframes[node_id]
    preview_df = df.head(req.limit)
    rows = preview_df.to_dicts()
    cols = preview_df.columns

    return ETLPreviewResponse(
        node_id=node_id,
        columns=cols,
        rows=rows,
        total_rows=len(df),
    )
