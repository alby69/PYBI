"""Tests for Semantic Model REST API v1 endpoints and Model View operations."""

import os
import pytest
from fastapi.testclient import TestClient
from pybi.api.main import app
from pybi.core.storage import default_storage
from pybi.core.semantic_model import (
    SemanticModel as CoreSemanticModel,
    SemanticTable as CoreSemanticTable,
    SemanticColumn as CoreSemanticColumn,
    SemanticRelationship as CoreSemanticRelationship,
)
from pybi.models.semantic import (
    TableMetadata,
    ColumnMetadata,
    Relationship,
    Measure,
    CardinalityType,
    CrossFilterDirection,
    JoinType,
)
from pybi.core.autodetect_relationships import autodetect_model_relationships

client = TestClient(app)


def test_semantic_api_endpoints(tmp_path):
    project_id = "test_semantic_proj_v2"

    # Pre-populate project with a semantic model
    t1 = CoreSemanticTable(
        name="sales",
        source_table="sales_tbl",
        columns=[
            CoreSemanticColumn(name="sale_id", column_name="sale_id", data_type="integer", is_key=True),
            CoreSemanticColumn(name="store_id", column_name="store_id", data_type="integer", is_key=False),
        ],
    )
    t2 = CoreSemanticTable(
        name="stores",
        source_table="stores_tbl",
        columns=[
            CoreSemanticColumn(name="store_id", column_name="store_id", data_type="integer", is_key=True),
            CoreSemanticColumn(name="store_name", column_name="store_name", data_type="string"),
        ],
    )
    rel = CoreSemanticRelationship(
        from_table="sales",
        from_column="store_id",
        to_table="stores",
        to_column="store_id",
        cardinality="*:1",
        join_type="LEFT",
        is_active=True,
    )
    model = CoreSemanticModel(
        name=f"{project_id}_semantic_model",
        tables=[t1, t2],
        relationships=[rel],
    )

    data_dir = default_storage.get_project_data_dir(project_id)
    yaml_path = os.path.join(data_dir, "semantic_model.yaml")
    model.save_yaml_file(yaml_path)

    # 1. GET /api/v1/projects/{project_id}/semantic
    res = client.get(f"/api/v1/projects/{project_id}/semantic")
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == f"{project_id}_semantic_model"
    assert len(data["tables"]) == 2

    # 2. GET /api/v1/projects/{project_id}/semantic/tables
    res = client.get(f"/api/v1/projects/{project_id}/semantic/tables")
    assert res.status_code == 200
    tables = res.json()
    assert len(tables) == 2
    assert tables[0]["name"] == "sales"

    # 3. PUT /api/v1/projects/{project_id}/semantic/relationships
    updated_rels = [
        {
            "id": "rel_sales_store_id_stores_store_id",
            "from_table": "sales",
            "from_column": "store_id",
            "to_table": "stores",
            "to_column": "store_id",
            "cardinality": "*:1",
            "cross_filter_direction": "single",
            "join_type": "LEFT",
            "is_active": False,
        }
    ]
    res = client.put(f"/api/v1/projects/{project_id}/semantic/relationships", json={"relationships": updated_rels})
    assert res.status_code == 200
    assert res.json()["relationships"][0]["is_active"] is False

    # 4. POST /api/v1/projects/{project_id}/semantic/relationships (Add single relationship)
    new_rel = {
        "id": "rel_custom_1",
        "from_table": "sales",
        "from_column": "sale_id",
        "to_table": "stores",
        "to_column": "store_id",
        "cardinality": "1:1",
        "cross_filter_direction": "both",
        "join_type": "INNER",
        "is_active": True,
    }
    res = client.post(f"/api/v1/projects/{project_id}/semantic/relationships", json=new_rel)
    assert res.status_code == 200
    assert res.json()["id"] == "rel_custom_1"

    # 5. DELETE /api/v1/projects/{project_id}/semantic/relationships/{rel_id}
    res = client.delete(f"/api/v1/projects/{project_id}/semantic/relationships/rel_custom_1")
    assert res.status_code == 200
    assert res.json()["status"] == "success"

    # 6. POST /api/v1/projects/{project_id}/semantic/measures
    new_measure = {
        "id": "meas_tot_sales",
        "name": "Totale Vendite",
        "table_name": "sales",
        "expression": "SUM(sales.amount)",
        "format_string": "€ #,##0.00",
    }
    res = client.post(f"/api/v1/projects/{project_id}/semantic/measures", json=new_measure)
    assert res.status_code == 200
    assert res.json()["name"] == "Totale Vendite"

    # 7. POST /api/v1/projects/{project_id}/semantic/relationships/autodetect
    res = client.post(f"/api/v1/projects/{project_id}/semantic/relationships/autodetect")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_autodetect_relationships_logic():
    tbl_orders = TableMetadata(
        name="orders",
        columns=[
            ColumnMetadata(name="order_id", data_type="integer", is_key=True),
            ColumnMetadata(name="customer_id", data_type="integer", is_key=False),
            ColumnMetadata(name="amount", data_type="float"),
        ],
    )
    tbl_customers = TableMetadata(
        name="customers",
        columns=[
            ColumnMetadata(name="customer_id", data_type="integer", is_key=True),
            ColumnMetadata(name="customer_name", data_type="string"),
        ],
    )

    detected = autodetect_model_relationships([tbl_orders, tbl_customers])
    assert len(detected) == 1
    rel = detected[0]
    assert rel.from_table == "orders"
    assert rel.from_column == "customer_id"
    assert rel.to_table == "customers"
    assert rel.to_column == "customer_id"
    assert rel.cardinality == CardinalityType.MANY_TO_ONE
    assert rel.is_active is True
