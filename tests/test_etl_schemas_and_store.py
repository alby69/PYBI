"""Tests for Power Query Editor Pydantic schemas, store architecture, and REST API preview endpoint."""

import polars as pl
import pytest
from fastapi.testclient import TestClient

from pybi.api.main import app
from pybi.core.storage import default_storage
from pybi.dashboard.binding import default_binder
from pybi.schemas.etl import ETLExecuteRequest, ETLPreviewRequest, ETLQuery, ETLStep

client = TestClient(app)


def test_etl_step_schema_and_aliases():
    """Verify ETLStep instantiation with primary fields and alias fallbacks."""
    # Using primary field names
    step1 = ETLStep(
        step_id="step_1",
        step_type="filter",
        name="Righe filtrate",
        description="Filtro per regione EU",
        params={"condition": "region = 'EU'"},
    )
    assert step1.step_id == "step_1"
    assert step1.step_type == "filter"
    assert step1.id == "step_1"
    assert step1.operation == "filter"
    assert step1.name == "Righe filtrate"

    # Using alias names (id and operation / type)
    step2 = ETLStep(
        id="step_2",
        operation="rename_column",
        name="Rinomina colonna",
        params={"mapping": {"val": "amount"}},
    )
    assert step2.step_id == "step_2"
    assert step2.step_type == "rename_column"
    assert step2.id == "step_2"
    assert step2.operation == "rename_column"


def test_etl_query_and_request_schemas():
    """Verify ETLQuery, ETLExecuteRequest and ETLPreviewRequest serialization."""
    step = ETLStep(
        step_id="step_1",
        step_type="filter",
        name="Filter step",
        params={"condition": "val > 10"},
    )
    query = ETLQuery(
        query_name="Sales",
        source={"table_name": "Sales"},
        steps=[step],
    )
    assert query.query_name == "Sales"
    assert len(query.steps) == 1

    exec_req = ETLExecuteRequest(query=query, target_table_name="Sales_Processed")
    assert exec_req.target_table_name == "Sales_Processed"
    assert exec_req.query.query_name == "Sales"

    preview_req = ETLPreviewRequest(query=query, step_index=0)
    assert preview_req.step_index == 0
    assert preview_req.query.steps[0].step_id == "step_1"


def test_etl_preview_api_endpoint(tmp_path):
    """Integration test for POST /api/v1/projects/{project_id}/etl/preview endpoint."""
    project_id = "test_pq_proj"
    if not default_storage.project_exists(project_id):
        client.post("/api/v1/projects", json={"project_id": project_id, "name": "Power Query Test Project"})

    # Register sample source table in default_binder / DuckDB
    df_sample = pl.DataFrame({
        "region": ["EU", "US", "EU", "APAC"],
        "amount": [100, 200, 150, 300],
    })
    default_binder.register_source("Customers", df_sample)

    payload = {
        "query": {
            "query_name": "Customers",
            "source": {"table_name": "Customers"},
            "steps": [
                {
                    "step_id": "step_1",
                    "step_type": "filter",
                    "name": "Filtro EU",
                    "params": {"condition": "region = 'EU'"},
                },
                {
                    "step_id": "step_2",
                    "step_type": "add_column",
                    "name": "Colonna Calcolata",
                    "params": {
                        "new_column": "double_amount",
                        "mode": "expression",
                        "expression": "amount * 2",
                    },
                },
            ],
        },
        "step_index": 2,  # Preview after step 2
    }

    res = client.post(f"/api/v1/projects/{project_id}/etl/preview", json=payload)
    assert res.status_code == 200, res.text
    data = res.json()

    assert "columns" in data
    assert "rows" in data
    assert "total_rows" in data
    assert "total_columns" in data
    assert "execution_time" in data

    assert data["total_rows"] == 2
    assert "double_amount" in data["columns"]
    assert len(data["rows"]) == 2


def test_etl_preview_api_step_0(tmp_path):
    """Test preview endpoint at step_index = 0 (initial source preview)."""
    project_id = "test_pq_proj_0"
    if not default_storage.project_exists(project_id):
        client.post("/api/v1/projects", json={"project_id": project_id, "name": "Power Query Test Project 0"})

    df_orders = pl.DataFrame({
        "id": [1, 2, 3],
        "status": ["pending", "shipped", "delivered"],
    })
    default_binder.register_source("Orders", df_orders)

    payload = {
        "query": {
            "query_name": "Orders",
            "source": {"table_name": "Orders"},
            "steps": [
                {
                    "step_id": "step_1",
                    "step_type": "filter",
                    "name": "Filter shipped",
                    "params": {"condition": "status = 'shipped'"},
                }
            ],
        },
        "step_index": 0,
    }

    res = client.post(f"/api/v1/projects/{project_id}/etl/preview", json=payload)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["total_rows"] == 3  # Initial source data (no steps applied yet)
    assert data["total_columns"] == 2
