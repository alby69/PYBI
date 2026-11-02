"""Compatibility exports and synchronous handlers for the historical ETL API."""

from typing import Any, Dict, Union

from fastapi import HTTPException, status

from pybi.api.schemas import DagSaveRequest
from pybi.api.v1 import etl as _canonical
from pybi.api.v1.etl import *
from pybi.core.storage import default_storage
from pybi.dashboard.binding import default_binder
from pybi.etl.executor import ETLExecutor
import pybi.storage.project_manager as pm

from backend.api.v1.models import (
    ETLDAGSchema,
    ETLPreviewRequest,
    ETLPreviewResponse,
    MessageResponse,
    SaveETLDAGRequest,
)


def get_etl_dag(project_id: str) -> ETLDAGSchema:
    """Fetch the project's ETL DAG using the historical synchronous contract."""
    if not default_storage.project_exists(project_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )
    dag_dict = pm.load_dag(project_id)
    return ETLDAGSchema(
        nodes=dag_dict.get("nodes", []),
        edges=dag_dict.get("edges", []),
        query_name=dag_dict.get("query_name"),
        source=dag_dict.get("source", {}),
        steps=dag_dict.get("steps", []),
    )


def save_etl_dag(
    project_id: str,
    req: Union[SaveETLDAGRequest, DagSaveRequest, Dict[str, Any]],
) -> MessageResponse:
    """Save ETL configuration using the historical synchronous contract."""
    if not default_storage.project_exists(project_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )

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


def preview_node_output(
    project_id: str,
    req: ETLPreviewRequest,
) -> ETLPreviewResponse:
    """Preview a pipeline node or step using the historical synchronous contract."""
    if not default_storage.project_exists(project_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )

    dag_dict = req.query.model_dump() if req.query else pm.load_dag(project_id)
    data_dir = default_storage.get_project_data_dir(project_id)
    executor = ETLExecutor(
        duckdb_conn=default_binder.duckdb_conn,
        base_dir=data_dir,
    )

    if req.step_index is not None:
        result = executor.execute_linear_etl(
            dag_dict,
            stop_at_step_index=req.step_index,
        )
        step_key = f"step_{req.step_index}"
        if step_key in result.dataframes:
            dataframe = result.dataframes[step_key]
        elif "source" in result.dataframes and req.step_index == 0:
            dataframe = result.dataframes["source"]
        elif result.output_tables:
            dataframe = next(iter(result.output_tables.values()))
        else:
            dataframe = None
    else:
        result = executor.execute(dag_dict)
        node_key = req.node_id or ""
        if node_key in result.dataframes:
            dataframe = result.dataframes[node_key]
        elif result.dataframes:
            dataframe = list(result.dataframes.values())[-1]
        else:
            dataframe = None

    if dataframe is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Specified node or step_index produced no dataframe output during execution",
        )

    preview = dataframe.head(req.limit)
    return ETLPreviewResponse(
        node_id=req.node_id,
        step_index=req.step_index,
        columns=preview.columns,
        rows=preview.to_dicts(),
        total_rows=len(dataframe),
    )


def __getattr__(name: str):
    return getattr(_canonical, name)
