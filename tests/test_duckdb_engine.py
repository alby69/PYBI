"""Unit tests for ETLEngine in pybi.etl.duckdb_engine and associated REST API endpoints."""

import os
import pytest
import pandas as pd
from fastapi.testclient import TestClient

from pybi.api.main import app
from pybi.core.storage import default_storage
from pybi.etl.duckdb_engine import ETLEngine
from pybi.schemas.etl import ETLQuery, ETLStep

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_duckdb_test_projects():
    """Clean up test project workspace before and after test execution."""
    test_pids = ["duckdb_engine_proj", "duckdb_api_proj"]
    for pid in test_pids:
        default_storage.delete_project(pid)
    yield
    for pid in test_pids:
        default_storage.delete_project(pid)


def test_to_duckdb_sql_cte_translation():
    """Test translation of JSON linear query steps into DuckDB SQL CTE clauses."""
    query = {
        "query_name": "Sales_Data",
        "source": {"type": "csv", "path": "sales_data.csv"},
        "steps": [
            {
                "id": "step_1",
                "name": "Filter Amount",
                "operation": "filter",
                "params": {"condition": "amount > 100"},
            },
            {
                "id": "step_2",
                "name": "Rename Col",
                "operation": "rename",
                "params": {"mapping": {"amount": "total_amount"}},
            },
            {
                "id": "step_3",
                "name": "Cast Type",
                "operation": "cast",
                "params": {"casts": {"total_amount": "FLOAT"}},
            },
        ],
    }

    # Full SQL compilation
    sql_full = ETLEngine.to_duckdb_sql(query)
    assert "WITH step_0 AS (" in sql_full
    assert "step_1 AS (" in sql_full
    assert "step_2 AS (" in sql_full
    assert "step_3 AS (" in sql_full
    assert "WHERE amount > 100" in sql_full
    assert "RENAME (\"amount\" AS \"total_amount\")" in sql_full
    assert "SELECT * FROM step_3" in sql_full

    # Partial compilation up to step_index = 1
    sql_step1 = ETLEngine.to_duckdb_sql(query, step_index=1)
    assert "step_1 AS (" in sql_step1
    assert "step_2 AS (" not in sql_step1
    assert "SELECT * FROM step_1" in sql_step1


def test_generate_preview_and_execute_full_pipeline():
    """Test preview generation with row limit and full pipeline execution."""
    pid = "duckdb_engine_proj"
    default_storage.save_project(pid, name="Engine Test Proj")

    # Save a CSV file in project data dir
    data_dir = default_storage.get_project_data_dir(pid)
    csv_path = os.path.join(data_dir, "test.csv")
    df_raw = pd.DataFrame({
        "category": ["A", "B", "A", "C", "B"] * 300,
        "amount": [10, 20, 30, 40, 50] * 300,
    })
    df_raw.to_csv(csv_path, index=False)

    query = {
        "query_name": "Preview_Query",
        "source": {"type": "csv", "path": "test.csv"},
        "steps": [
            {
                "id": "s1",
                "name": "Filter Category",
                "operation": "filter",
                "params": {"condition": "category = 'A'"},
            }
        ],
    }

    # Generate preview with limit = 100 returning Polars DataFrame up to step_index 1
    df_prev = ETLEngine.generate_preview(pid, query, step_index=1, limit=100)
    import polars as pl
    assert isinstance(df_prev, pl.DataFrame)
    assert len(df_prev) == 100
    assert (df_prev["category"] == "A").all()

    # Execute full pipeline
    result = ETLEngine.execute_full_pipeline(pid, query, target_table="a_categories")
    assert result["status"] == "completed"
    assert result["target_table"] == "a_categories"
    assert result["rows"] == 600


def test_build_sql_query_advanced_steps():
    """Test build_sql_query with split_column, merge, custom_column, group_by, rename, and remove_columns."""
    query = {
        "query_name": "Advanced_Query",
        "source": {"type": "csv", "path": "users.csv"},
        "steps": [
            {
                "id": "s1",
                "name": "Split Name",
                "operation": "split_column",
                "params": {
                    "column": "full_name",
                    "delimiter": " ",
                    "parts": 2,
                    "new_columns": ["first_name", "last_name"],
                },
            },
            {
                "id": "s2",
                "name": "Custom Full Name",
                "operation": "custom_column",
                "params": {
                    "column_name": "Full_Display",
                    "expression": "CONCAT(first_name, ' ', last_name)",
                },
            },
            {
                "id": "s3",
                "name": "Remove Unneeded",
                "operation": "remove_columns",
                "params": {"columns": ["full_name"]},
            },
            {
                "id": "s4",
                "name": "Rename ID",
                "operation": "rename",
                "params": {"old_name": "user_id", "new_name": "id"},
            },
            {
                "id": "s5",
                "name": "Group By Category",
                "operation": "group_by",
                "params": {
                    "group_by_columns": ["category"],
                    "aggregations": "SUM(sales) AS TotalSales",
                },
            },
        ],
    }

    sql = ETLEngine.build_sql_query(query, step_index=5)
    assert "string_split(\"full_name\", ' ')[1] AS \"first_name\"" in sql
    assert "(CONCAT(first_name, ' ', last_name)) AS \"Full_Display\"" in sql
    assert "EXCLUDE (\"full_name\")" in sql
    assert "RENAME (\"user_id\" AS \"id\")" in sql
    assert "GROUP BY \"category\"" in sql
    assert "SUM(sales) AS TotalSales" in sql


def test_save_and_load_query():
    """Test saving and loading ETL query configurations via ETLEngine."""
    pid = "duckdb_engine_proj"
    default_storage.save_project(pid, name="Query Test Proj")

    query = ETLQuery(
        query_name="Stored_Query",
        source={"type": "csv", "path": "data.csv"},
        steps=[
            ETLStep(
                step_id="step_1",
                step_type="filter",
                name="Filter",
                params={"condition": "val > 0"},
            )
        ],
    )

    saved = ETLEngine.save_query(pid, query)
    assert saved is True

    loaded = ETLEngine.load_query(pid)
    assert loaded is not None
    assert loaded["query_name"] == "Stored_Query"
    assert len(loaded["steps"]) == 1


def test_etl_rest_api_endpoints():
    """Integration test for ETL REST API endpoints in pybi.api.v1.etl."""
    pid = "duckdb_api_proj"

    # Create project
    client.post("/api/v1/projects", json={"project_id": pid, "name": "ETL API Test"})

    # Upload sample file
    csv_bytes = b"item,price\nPen,10\nNotebook,50\nEraser,5\nBinder,30\n"
    client.post(
        f"/api/v1/projects/{pid}/files",
        files={"file": ("items.csv", csv_bytes, "text/csv")},
    )

    query_payload = {
        "query_name": "Items_Query",
        "source": {"type": "csv", "path": "items.csv"},
        "steps": [
            {
                "id": "step_1",
                "name": "Filter Price",
                "operation": "filter",
                "params": {"condition": "price >= 10"},
            }
        ],
    }

    # 1. PUT /query
    save_res = client.put(f"/api/v1/projects/{pid}/etl/query", json={"query": query_payload})
    assert save_res.status_code == 200
    assert save_res.json()["status"] == "success"

    # 2. GET /query
    get_res = client.get(f"/api/v1/projects/{pid}/etl/query")
    assert get_res.status_code == 200
    assert get_res.json()["query_name"] == "Items_Query"

    # 3. POST /preview
    prev_res = client.post(
        f"/api/v1/projects/{pid}/etl/preview",
        json={"project_id": pid, "query": query_payload, "step_index": 1, "limit": 1000},
    )
    assert prev_res.status_code == 200
    prev_data = prev_res.json()
    assert prev_data["total_rows"] == 3
    assert "price" in prev_data["columns"]
    assert "execution_time" in prev_data

    # 4. POST /execute
    exec_res = client.post(
        f"/api/v1/projects/{pid}/etl/execute",
        json={"project_id": pid, "query": query_payload, "target_table_name": "expensive_items"},
    )
    assert exec_res.status_code == 200
    exec_data = exec_res.json()
    assert exec_data["status"] == "success"
    assert "job_id" in exec_data

    # 5. GET /jobs/{job_id}
    job_id = exec_data["job_id"]
    job_res = client.get(f"/api/v1/projects/{pid}/etl/jobs/{job_id}")
    assert job_res.status_code == 200
    assert job_res.json()["status"] == "success"
