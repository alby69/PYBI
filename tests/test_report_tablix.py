"""Unit tests for ReportTablix component and GROUP BY ROLLUP preview API endpoint."""

from fastapi.testclient import TestClient
import polars as pl
import pytest

from pybi.api.main import app
from pybi.dashboard.binding import default_binder
from pybi.ui.components.report_tablix import ReportTablix

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_data():
    sample_df = pl.DataFrame({
        "year": ["2023", "2023", "2024", "2024"],
        "region": ["Europe", "North America", "Europe", "North America"],
        "revenue": [1000, 1500, 1200, 1800],
        "units": [10, 15, 12, 18]
    })
    default_binder.register_source("sales_report_data", sample_df)
    yield


def test_report_tablix_component_initialization():
    tablix = ReportTablix(
        data=[{"year": "2023", "revenue": 1000}],
        columns=["year", "revenue"],
        row_groups=["year"],
        measures=[{"col": "revenue", "agg": "Sum", "title": "Revenue"}],
        conditional_formatting=[{"column": "revenue", "operator": ">", "value": 500, "style": {"color": "green"}}],
        show_grand_total=True,
    )
    assert tablix._row_groups == ["year"]
    assert tablix._props["showGrandTotal"] is True
    assert len(tablix._conditional_formatting) == 1


def test_tablix_preview_rollup_endpoint():
    payload = {
        "project_id": "default",
        "table_name": "sales_report_data",
        "row_groups": ["year", "region"],
        "measures": [{"col": "revenue", "agg": "SUM", "title": "Total Revenue"}],
        "filter_context": {"year": ["2023"]}
    }

    res = client.post("/api/v1/viewer/reports/rep_1/preview", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["report_id"] == "rep_1"
    assert "GROUP BY ROLLUP" in data["sql"]
    assert data["row_count"] > 0
    assert "Total Revenue" in data["columns"]
