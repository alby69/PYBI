"""Tests for the Power BI style Report View API, storage and component suite."""

import os
import zipfile

import pytest
from fastapi.testclient import TestClient

from pybi.api.main import app
from pybi.core.report_storage import REPORT_LAYOUT_FILENAME, get_report_layout_path
from pybi.core.storage import default_storage

client = TestClient(app)
PROJECT_ID = "v1_report_proj"


@pytest.fixture(autouse=True)
def clean_report_project():
    """Remove the report test project before and after each test."""
    default_storage.delete_project(PROJECT_ID)
    yield
    default_storage.delete_project(PROJECT_ID)


def _create_project_with_sales() -> None:
    response = client.post(
        "/api/v1/projects",
        json={"project_id": PROJECT_ID, "name": "Report View Test"},
    )
    assert response.status_code == 201
    csv_bytes = b"category,amount,region\nA,100,North\nB,200,South\nA,300,North\n"
    response = client.post(
        f"/api/v1/projects/{PROJECT_ID}/files",
        files={"file": ("sales.csv", csv_bytes, "text/csv")},
    )
    assert response.status_code == 201


def _sample_layout() -> dict:
    return {
        "project_id": PROJECT_ID,
        "active_page_id": "page_sales",
        "theme": "PowerBI_Dark",
        "report_filters": [],
        "pages": [
            {
                "id": "page_sales",
                "name": "Vendite",
                "is_hidden": False,
                "page_type": "Standard",
                "width": 1280,
                "height": 720,
                "page_filters": [],
                "visuals": [
                    {
                        "id": "vis_sales",
                        "type": "bar_chart",
                        "title": "Vendite per categoria",
                        "position": {"x": 40, "y": 40, "width": 480, "height": 300, "z_index": 1},
                        "data_buckets": {
                            "x_axis": [
                                {
                                    "table": "sales",
                                    "column": "category",
                                    "name": "category",
                                    "kind": "column",
                                    "data_type": "string",
                                }
                            ],
                            "y_axis": [
                                {
                                    "table": "sales",
                                    "column": "amount",
                                    "name": "amount",
                                    "kind": "column",
                                    "data_type": "number",
                                    "aggregation": "SUM",
                                }
                            ],
                        },
                        "properties": {"table_name": "sales"},
                        "filters": [],
                    }
                ],
            }
        ],
    }


def test_report_layout_roundtrip_and_storage_path():
    _create_project_with_sales()

    response = client.get(f"/api/v1/projects/{PROJECT_ID}/report")
    assert response.status_code == 200
    layout = response.json()
    assert layout["project_id"] == PROJECT_ID
    assert len(layout["pages"]) == 1
    assert layout["pages"][0]["width"] == 1280

    payload = _sample_layout()
    response = client.put(f"/api/v1/projects/{PROJECT_ID}/report", json=payload)
    assert response.status_code == 200
    saved = response.json()
    assert saved["theme"] == "PowerBI_Dark"
    assert saved["pages"][0]["visuals"][0]["title"] == "Vendite per categoria"

    assert os.path.exists(get_report_layout_path(PROJECT_ID))
    assert REPORT_LAYOUT_FILENAME in os.listdir(default_storage.get_project_data_dir(PROJECT_ID))

    response = client.get(f"/api/v1/projects/{PROJECT_ID}/report")
    assert response.status_code == 200
    assert response.json()["pages"][0]["id"] == "page_sales"


def test_report_tables_and_data_view_endpoints():
    _create_project_with_sales()

    response = client.get(f"/api/v1/projects/{PROJECT_ID}/report/tables")
    assert response.status_code == 200
    tables = response.json()
    assert any(table["name"] == "sales" for table in tables)
    sales = next(table for table in tables if table["name"] == "sales")
    assert {"category", "amount", "region"}.issubset({column["name"] for column in sales["columns"]})

    response = client.get(
        f"/api/v1/projects/{PROJECT_ID}/report/tables/sales/data",
        params={"limit": 2, "sort_by": "amount", "sort_dir": "desc"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_rows"] == 3
    assert len(data["rows"]) == 2
    assert data["rows"][0]["amount"] >= data["rows"][1]["amount"]

    response = client.get(
        f"/api/v1/projects/{PROJECT_ID}/report/tables/sales/data",
        params={"search": "South"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filtered_rows"] == 1
    assert data["rows"][0]["region"] == "South"

    response = client.get(
        f"/api/v1/projects/{PROJECT_ID}/report/tables/sales/values",
        params={"column": "category"},
    )
    assert response.status_code == 200
    assert response.json() == ["A", "B"]


def test_report_visual_data_and_exports():
    _create_project_with_sales()
    payload = {"widget": _sample_layout()["pages"][0]["visuals"][0], "filters": []}

    response = client.post(f"/api/v1/projects/{PROJECT_ID}/report/visual-data", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["columns"] == ["category", "value"]
    assert data["row_count"] == 2
    totals = {row["category"]: row["value"] for row in data["rows"]}
    assert totals["A"] == 400
    assert totals["B"] == 200
    assert "GROUP BY" in data["generated_sql"]

    filtered = {"widget": payload["widget"], "filters": [{"field": "region", "mode": "basic", "values": ["South"]}]}
    response = client.post(f"/api/v1/projects/{PROJECT_ID}/report/visual-data", json=filtered)
    assert response.status_code == 200
    assert response.json()["rows"] == [{"category": "B", "value": 200}]

    topn = {
        "widget": {**payload["widget"], "properties": {**payload["widget"]["properties"], "sort_by": "category"}},
        "filters": [{"field": "category", "mode": "top_n", "top_n": 1, "top_direction": "top", "by": "value"}],
    }
    response = client.post(f"/api/v1/projects/{PROJECT_ID}/report/visual-data", json=topn)
    assert response.status_code == 200
    topn_data = response.json()
    assert topn_data["row_count"] == 1
    assert topn_data["rows"] == [{"category": "A", "value": 400}]
    assert topn_data["generated_sql"].count("ORDER BY") == 1

    export_payload = {"columns": data["columns"], "rows": data["rows"], "filename": "vendite"}
    response = client.post(
        f"/api/v1/projects/{PROJECT_ID}/report/export",
        json={**export_payload, "format": "csv"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert b"category,value" in response.content
    assert b"A,400" in response.content

    response = client.post(
        f"/api/v1/projects/{PROJECT_ID}/report/export",
        json={**export_payload, "format": "xlsx"},
    )
    assert response.status_code == 200
    assert response.content[:2] == b"PK"
    with zipfile.ZipFile(__import__("io").BytesIO(response.content)) as archive:
        names = archive.namelist()
        assert "xl/workbook.xml" in names
        assert "xl/worksheets/sheet1.xml" in names
        assert b"A" in archive.read("xl/worksheets/sheet1.xml")


def test_report_endpoints_require_existing_project():
    response = client.get("/api/v1/projects/does_not_exist/report")
    assert response.status_code == 404
    response = client.post(
        "/api/v1/projects/does_not_exist/report/visual-data",
        json={"widget": {}, "filters": []},
    )
    assert response.status_code == 404


def test_report_component_files_and_registry_wrappers():
    base = os.path.join("pybi", "ui", "components")
    expected = [
        os.path.join(base, "report", "ReportCanvas.vue"),
        os.path.join(base, "report", "PageTabBar.vue"),
        os.path.join(base, "report", "FiltersPane.vue"),
        os.path.join(base, "report", "VisualizationsPane.vue"),
        os.path.join(base, "report", "FormattingPane.vue"),
        os.path.join(base, "report", "VisualHeader.vue"),
        os.path.join(base, "report", "VisualRenderer.vue"),
        os.path.join(base, "data", "DataPane.vue"),
        os.path.join(base, "data", "DataTableView.vue"),
        os.path.join(base, "shell", "MainShell.vue"),
        os.path.join("pybi", "ui", "stores", "reportStore.js"),
        os.path.join("pybi", "ui", "stores", "themeStore.js"),
        os.path.join("pybi", "ui", "assets", "powerbi-theme.css"),
    ]
    for path in expected:
        assert os.path.exists(path), f"Missing Report View file: {path}"

    from pybi.ui.components import report_registry as registry

    expected_tags = {
        "ReportMainShell": "nicegui-MainShell",
        "ReportCanvas": "nicegui-ReportCanvas",
        "FiltersPane": "nicegui-FiltersPane",
        "VisualizationsPane": "nicegui-VisualizationsPane",
        "FormattingPane": "nicegui-FormattingPane",
        "VisualHeader": "nicegui-VisualHeader",
        "VisualRenderer": "nicegui-VisualRenderer",
        "PageTabBar": "nicegui-PageTabBar",
        "DataPane": "nicegui-DataPane",
        "DataTableView": "nicegui-DataTableView",
    }
    for class_name, expected_tag in expected_tags.items():
        component = getattr(registry, class_name).component
        assert component is not None
        assert component.tag == expected_tag

    shell = registry.ReportMainShell(project_id="demo")
    assert shell._props["projectId"] == "demo"
    shell.set_project_id("other")
    assert shell._props["projectId"] == "other"
