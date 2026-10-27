"""Tests for Semantic Model REST API v1 endpoints."""

import os
import pytest
from fastapi.testclient import TestClient
from pybi.api.main import app
from pybi.core.storage import default_storage
from pybi.core.semantic_model import (
    SemanticModel,
    SemanticTable,
    SemanticColumn,
    SemanticRelationship,
)

client = TestClient(app)


def test_semantic_api_endpoints(tmp_path):
    project_id = "test_semantic_proj"

    # Pre-populate project with a semantic model
    t1 = SemanticTable(
        name="sales",
        source_table="sales_tbl",
        columns=[
            SemanticColumn(name="sale_id", column_name="sale_id", data_type="integer", is_key=True),
            SemanticColumn(name="store_id", column_name="store_id", data_type="integer", is_key=False),
        ],
    )
    t2 = SemanticTable(
        name="stores",
        source_table="stores_tbl",
        columns=[
            SemanticColumn(name="store_id", column_name="store_id", data_type="integer", is_key=True),
            SemanticColumn(name="store_name", column_name="store_name", data_type="string"),
        ],
    )
    rel = SemanticRelationship(
        from_table="sales",
        from_column="store_id",
        to_table="stores",
        to_column="store_id",
        cardinality="*:1",
        join_type="LEFT",
        is_active=True,
    )
    model = SemanticModel(
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
            "from_table": "sales",
            "from_column": "store_id",
            "to_table": "stores",
            "to_column": "store_id",
            "cardinality": "*:1",
            "join_type": "LEFT",
            "is_active": False,
        }
    ]
    res = client.put(f"/api/v1/projects/{project_id}/semantic/relationships", json={"relationships": updated_rels})
    assert res.status_code == 200
    assert res.json()["relationships"][0]["is_active"] is False

    # 4. POST /api/v1/projects/{project_id}/semantic/autodetect
    res = client.post(f"/api/v1/projects/{project_id}/semantic/autodetect")
    assert res.status_code == 200
    # Relationship already exists in model so autodetect returns empty list or newly detected pairs
    assert isinstance(res.json(), list)
