"""Tests for MCP (Model Context Protocol) Tools and Router."""

import json
from fastapi.testclient import TestClient
from backend.main import app
from backend.mcp.tools import (
    execute_analytical_query,
    get_data_lineage,
    get_semantic_schema,
    validate_dax_expression,
)

client = TestClient(app)


def test_get_semantic_schema_tool():
    res = get_semantic_schema("default")
    data = json.loads(res)
    assert "tables" in data
    assert "relationships" in data


def test_validate_dax_expression_tool():
    res = validate_dax_expression("DIVIDE(SUM(sales), SUM(units))", "default")
    assert res["status"] == "success"
    assert "COALESCE" in res["translated_sql"]


def test_execute_analytical_query_tool():
    res = execute_analytical_query("SELECT 42 AS value", "default")
    assert res["status"] == "success"
    assert res["rows"] == [(42,)] or res["rows"] == [[42]]


def test_get_data_lineage_tool():
    res = get_data_lineage("default")
    assert res["status"] == "success"
    assert "lineage" in res


def test_mcp_api_schema_endpoint():
    res = client.get("/api/v1/mcp/schema/default")
    assert res.status_code == 200
    assert res.json()["status"] == "success"


def test_mcp_api_validate_dax_endpoint():
    res = client.post(
        "/api/v1/mcp/validate-dax",
        json={"dax_expression": "DIVIDE(SUM(A), SUM(B))", "project_id": "default"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "success"


def test_mcp_api_invoke_tool_endpoint():
    res = client.post(
        "/api/v1/mcp/tools/validate_dax_expression",
        json={"dax_expression": "AVERAGE(amount)", "project_id": "default"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "success"
