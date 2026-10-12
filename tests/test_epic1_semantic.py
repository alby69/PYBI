"""Tests for Epic 1: Semantic Layer & Data Modeling."""

import duckdb
from fastapi.testclient import TestClient
import polars as pl
import pytest

from pybi.api.main import app
from pybi.core.semantic_model import (
    Cardinality,
    CoreSemanticModel,
    JoinType,
    SemanticColumn,
    SemanticMeasure,
    SemanticRelationship,
    SemanticTable,
)
from pybi.core.storage import default_storage
from pybi.semantic.engine import SemanticQueryResolver
from pybi.semantic.models import SemanticQueryRequest

client = TestClient(app)


def test_semantic_model_yaml_roundtrip(tmp_path):
    model = CoreSemanticModel(
        name="sales_model",
        tables=[
            SemanticTable(
                name="sales",
                source_table="sales_table",
                columns=[
                    SemanticColumn(name="sales_id", column_name="id", is_key=True),
                    SemanticColumn(name="customer_id", column_name="cust_id"),
                    SemanticColumn(name="amount", column_name="amount", data_type="float"),
                ],
                measures=[
                    SemanticMeasure(name="total_sales", expression="SUM(sales.amount)"),
                ],
            ),
            SemanticTable(
                name="customers",
                source_table="customers_table",
                columns=[
                    SemanticColumn(name="customer_id", column_name="id", is_key=True),
                    SemanticColumn(name="region", column_name="region"),
                ],
            ),
        ],
        relationships=[
            SemanticRelationship(
                from_table="sales",
                from_column="customer_id",
                to_table="customers",
                to_column="customer_id",
                cardinality=Cardinality.MANY_TO_ONE,
                join_type=JoinType.LEFT,
            )
        ],
    )

    yaml_str = model.to_yaml()
    assert "sales_model" in yaml_str
    assert "customers" in yaml_str

    reloaded = CoreSemanticModel.from_yaml(yaml_str)
    assert reloaded.name == model.name
    assert len(reloaded.tables) == 2
    assert len(reloaded.relationships) == 1
    assert reloaded.relationships[0].cardinality == Cardinality.MANY_TO_ONE


def test_semantic_query_resolver_multi_table_join():
    conn = duckdb.connect(database=":memory:")

    sales_df = pl.DataFrame({
        "id": [1, 2, 3, 4],
        "cust_id": [101, 102, 101, 103],
        "amount": [100.0, 200.0, 150.0, 300.0],
    })

    customers_df = pl.DataFrame({
        "id": [101, 102, 103],
        "region": ["EU", "US", "EU"],
    })

    conn.register("sales_table", sales_df)
    conn.register("customers_table", customers_df)

    model = CoreSemanticModel(
        name="test_join_model",
        tables=[
            SemanticTable(
                name="sales",
                source_table="sales_table",
                columns=[
                    SemanticColumn(name="sales_id", column_name="id", is_key=True),
                    SemanticColumn(name="customer_id", column_name="cust_id"),
                    SemanticColumn(name="amount", column_name="amount"),
                ],
                measures=[
                    SemanticMeasure(name="total_amount", expression='SUM("sales"."amount")'),
                ],
            ),
            SemanticTable(
                name="customers",
                source_table="customers_table",
                columns=[
                    SemanticColumn(name="customer_id", column_name="id", is_key=True),
                    SemanticColumn(name="region", column_name="region"),
                ],
            ),
        ],
        relationships=[
            SemanticRelationship(
                from_table="sales",
                from_column="customer_id",
                to_table="customers",
                to_column="customer_id",
                cardinality="*:1",
                join_type="LEFT",
            )
        ],
        default_table="sales",
    )

    resolver = SemanticQueryResolver(duckdb_conn=conn)
    resolver.register_model(model)

    req = SemanticQueryRequest(
        model_name="test_join_model",
        dimensions=["customers.region"],
        measures=["sales.total_amount"],
    )

    resp = resolver.execute(req)
    assert resp.row_count == 2

    region_totals = {r["customers_region"]: r["sales_total_amount"] for r in resp.rows}
    assert region_totals["EU"] == 550.0
    assert region_totals["US"] == 200.0


def test_semantic_schema_api_endpoints():
    pid = "test_epic1_project"
    if default_storage.project_exists(pid):
        default_storage.delete_project(pid)

    res_create = client.post("/api/v1/projects", json={"name": "Test Epic1", "project_id": pid})
    assert res_create.status_code == 201

    res_get = client.get(f"/api/v1/projects/{pid}/semantic/schema")
    assert res_get.status_code == 200
    schema_data = res_get.json()
    assert "tables" in schema_data

    schema_data["tables"] = [
        {
            "name": "orders",
            "source_table": "orders_table",
            "columns": [{"name": "order_id", "column_name": "id"}],
            "measures": [],
        }
    ]

    res_save = client.post(f"/api/v1/projects/{pid}/semantic/schema", json=schema_data)
    assert res_save.status_code == 200
    assert res_save.json()["schema"]["tables"][0]["name"] == "orders"

    res_reget = client.get(f"/api/v1/projects/{pid}/semantic/schema")
    assert res_reget.status_code == 200
    assert res_reget.json()["tables"][0]["name"] == "orders"

    default_storage.delete_project(pid)
