"""Unit tests for ReportParameters component and semantic parameters API endpoint."""

from fastapi.testclient import TestClient
import polars as pl
import pytest

from pybi.api.main import app
from pybi.dashboard.binding import default_binder
from pybi.ui.components.report_parameters import ReportParameters

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_param_test_data():
    sample_df = pl.DataFrame({
        "country": ["Italy", "Italy", "France", "Germany"],
        "region": ["Lombardia", "Lazio", "Île-de-France", "Bavaria"],
        "sales": [500, 300, 400, 600]
    })
    default_binder.register_source("param_regional_sales", sample_df)
    yield


def test_report_parameters_component_initialization():
    panel = ReportParameters(
        project_id="p1",
        parameters=[
            {"name": "Country", "table": "param_regional_sales", "column": "country"},
            {"name": "Region", "table": "param_regional_sales", "column": "region", "dependsOn": "Country"}
        ],
        initial_values={"Country": ["Italy"]}
    )

    assert panel._project_id == "p1"
    assert len(panel._parameters) == 2
    assert panel._initial_values == {"Country": ["Italy"]}


def test_semantic_parameters_api_cascading():
    # 1. Fetch parent options (country)
    payload_parent = {
        "table_name": "param_regional_sales",
        "column_name": "country"
    }
    res = client.post("/api/v1/projects/default/semantic/parameters", json=payload_parent)
    assert res.status_code == 200
    data = res.json()
    assert "France" in data["options"]
    assert "Italy" in data["options"]

    # 2. Fetch child options filtered by parent (Country = Italy)
    payload_child = {
        "table_name": "param_regional_sales",
        "column_name": "region",
        "parent_filters": {"country": ["Italy"]}
    }
    res_child = client.post("/api/v1/projects/default/semantic/parameters", json=payload_child)
    assert res_child.status_code == 200
    data_child = res_child.json()

    assert "Lombardia" in data_child["options"]
    assert "Lazio" in data_child["options"]
    assert "Bavaria" not in data_child["options"]
