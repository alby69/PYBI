"""MCP API Router for PyBI Model Context Protocol endpoints."""

from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.mcp.tools import (
    execute_analytical_query,
    get_data_lineage,
    get_semantic_schema,
    validate_dax_expression,
)

router = APIRouter(prefix="/api/v1/mcp", tags=["MCP AI Integration"])


class ValidateDaxRequest(BaseModel):
    dax_expression: str = Field(..., description="DAX expression string to translate and validate")
    project_id: str = Field(default="default", description="Project ID")


class ExecuteQueryRequest(BaseModel):
    query: str = Field(..., description="DAX or SQL query string")
    project_id: str = Field(default="default", description="Project ID")
    limit: int = Field(default=100, ge=1, le=500, description="Maximum row limit")


@router.get("/schema/{project_id}", summary="Get Semantic Model Schema for AI")
def api_get_semantic_schema(project_id: str):
    """Retrieve semantic model schema as JSON string for LLM/MCP prompt context."""
    schema_json = get_semantic_schema(project_id)
    return {"status": "success", "schema": schema_json}


@router.post("/validate-dax", summary="Validate DAX Expression")
def api_validate_dax(req: ValidateDaxRequest):
    """Translate DAX expression to SQL and validate syntax."""
    return validate_dax_expression(req.dax_expression, req.project_id)


@router.post("/execute-query", summary="Execute Analytical Query")
def api_execute_query(req: ExecuteQueryRequest):
    """Execute analytical query against project DuckDB store."""
    return execute_analytical_query(req.query, req.project_id, req.limit)


@router.get("/lineage/{project_id}", summary="Get Data Lineage")
def api_get_lineage(project_id: str):
    """Retrieve ETL data lineage and step transformations."""
    return get_data_lineage(project_id)


@router.post("/tools/{tool_name}", summary="Invoke MCP Tool")
def api_invoke_tool(tool_name: str, payload: Dict[str, Any]):
    """Generic tool invocation wrapper for MCP tool execution."""
    project_id = payload.get("project_id", "default")
    if tool_name == "get_semantic_schema":
        return {"status": "success", "result": get_semantic_schema(project_id)}
    elif tool_name in ("validate_dax_expression", "translate_and_validate_dax"):
        expr = payload.get("dax_expression", "")
        return validate_dax_expression(expr, project_id)
    elif tool_name == "execute_analytical_query":
        query = payload.get("query", "")
        limit = payload.get("limit", 100)
        return execute_analytical_query(query, project_id, limit)
    elif tool_name == "get_data_lineage":
        return get_data_lineage(project_id)
    else:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
