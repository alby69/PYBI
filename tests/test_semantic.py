"""Tests for PyBI Semantic Layer and FastAPI endpoint."""

import polars as pl
import pytest
from fastapi.testclient import TestClient

from pybi.api.main import app
from pybi.core.storage import default_storage
from pybi.dashboard.binding import default_binder
from pybi.semantic import (
    Dimension,
    Measure,
    SemanticModel,
    SemanticQueryRequest,
    SemanticQueryResolver,
)

client = TestClient(app)


def test_semantic_query_resolver():
    df = pl.DataFrame({
        "region": ["North", "South", "North", "East", "West"],
        "category": ["A", "A", "B", "B", "A"],
        "amount": [100, 200, 150, 300, 250],
    })

    model = SemanticModel(
        name="sales_model",
        source_table="sales_tbl",
        dimensions=[
            Dimension(name="Region", column_name="region"),
            Dimension(name="Category", column_name="category"),
        ],
        measures=[
            Measure(name="TotalAmount", column_name="amount", agg_func="SUM"),
        ],
    )

    resolver = SemanticQueryResolver()
    resolver.register_model(model)

    req = SemanticQueryRequest(
        model_name="sales_model",
        dimensions=["Region"],
        measures=["TotalAmount"],
        filters={"amount": {">=": 150}},
    )

    resp = resolver.execute(req, source_df=df)

    assert resp.row_count > 0
    assert "Region" in resp.columns or "region" in resp.columns
    assert "TotalAmount" in resp.columns
    assert "GROUP BY" in resp.generated_sql.upper()
    assert "WHERE" in resp.generated_sql.upper()


def test_semantic_query_api_endpoint(tmp_path):
    import os, shutil
    project_id = "test_semantic_proj"
    proj_path = default_storage._get_project_path(project_id)
    if os.path.isdir(proj_path):
        shutil.rmtree(proj_path)
    default_storage.save_project(project_id=project_id, name="Semantic Test Proj")

    df = pl.DataFrame({
        "region": ["North", "South", "North"],
        "sales": [500, 200, 300],
    })
    default_binder.register_source("regional_sales_api", df)

    payload = {
        "source_table": "regional_sales_api",
        "dimensions": ["region"],
        "measures": ["sales"],
        "filters": {"sales": {">": 250}},
    }

    res = client.post(f"/api/v1/viewer/{project_id}/semantic-query", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["row_count"] == 1
    assert "region" in data["columns"]
    assert "sales" in data["columns"]
