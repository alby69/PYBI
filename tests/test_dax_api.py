import pytest
from fastapi.testclient import TestClient

from pybi.api.main import app
from pybi.core.dax_engine import DAXEngine


def test_dax_engine_validation():
    engine = DAXEngine(semantic_model={"tables": [{"name": "Sales"}, {"name": "Customer"}]})

    # Empty formula
    res_empty = engine.validate_expression("")
    assert not res_empty.is_valid
    assert len(res_empty.errors) > 0

    # Unbalanced parentheses
    res_parens = engine.validate_expression("Total Sales = SUM(Sales[Amount]")
    assert not res_parens.is_valid
    assert "Parentesi non bilanciate" in res_parens.errors[0].message

    # Valid expression with refs
    res_valid = engine.validate_expression("Total Sales = CALCULATE(SUM('Sales'[Amount]), 'Customer'[Country] = \"Italy\")")
    assert res_valid.is_valid
    assert res_valid.measure_name == "Total Sales"
    assert "Sales" in res_valid.referenced_tables or "Customer" in res_valid.referenced_tables
    assert "Amount" in res_valid.referenced_columns or "Country" in res_valid.referenced_columns


def test_dax_engine_autocomplete():
    engine = DAXEngine(semantic_model={"tables": [{"name": "Sales"}, {"name": "Customer"}]})

    suggestions = engine.get_autocomplete_suggestions("CALC")
    assert any(s.label == "CALCULATE" for s in suggestions)

    suggestions_table = engine.get_autocomplete_suggestions("Sal")
    assert any(s.label == "'Sales'" for s in suggestions_table)


def test_dax_api_endpoints():
    client = TestClient(app)
    project_id = "p123"

    # 1. Validate endpoint
    val_payload = {
        "expression": "Total Sales = SUM('Sales'[Amount])",
        "current_table": "Sales",
        "project_id": project_id,
    }
    res_val = client.post(f"/api/v1/projects/{project_id}/dax/validate", json=val_payload)
    assert res_val.status_code == 200
    val_data = res_val.json()
    assert val_data["is_valid"] is True
    assert val_data["measure_name"] == "Total Sales"

    # 2. Autocomplete endpoint
    auto_payload = {
        "expression": "SUM",
        "cursor_position": 3,
        "project_id": project_id,
    }
    res_auto = client.post(f"/api/v1/projects/{project_id}/dax/autocomplete", json=auto_payload)
    assert res_auto.status_code == 200
    auto_data = res_auto.json()
    assert "suggestions" in auto_data
    assert any(s["label"] == "SUM" or s["label"] == "SUMX" for s in auto_data["suggestions"])

    # 3. Measures CRUD endpoint
    measure_payload = {
        "id": "m1",
        "name": "Total Sales",
        "table_name": "Sales",
        "expression": "Total Sales = SUM('Sales'[Amount])",
        "format_string": "#,##0.00 €",
        "is_hidden": False,
        "dependencies": ["Sales", "Amount"],
    }
    res_m = client.post(f"/api/v1/projects/{project_id}/dax/measures", json=measure_payload)
    assert res_m.status_code == 200
    m_data = res_m.json()
    assert m_data["id"] == "m1"
    assert m_data["name"] == "Total Sales"
