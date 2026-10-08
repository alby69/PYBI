"""Tests for UI Schema Declarative Engine and API Endpoints."""

import pytest
from fastapi.testclient import TestClient

from pybi.api.main import app
from pybi.server.ui_schema import ComponentSchema, UISchema, get_viewer_schema, get_etl_editor_schema

client = TestClient(app)


def test_component_schema_models():
    """Verify Pydantic models for declarative UI schema serialization."""
    comp = ComponentSchema(
        type="q-btn",
        props={"label": "Click Me", "color": "primary"},
        text="Click",
        action="api:POST:/api/etl/execute",
        children=[
            ComponentSchema(type="q-icon", props={"name": "star"})
        ]
    )
    data = comp.model_dump()
    assert data["type"] == "q-btn"
    assert data["props"]["label"] == "Click Me"
    assert len(data["children"]) == 1
    assert data["children"][0]["type"] == "q-icon"


def test_ui_schema_models():
    """Verify UISchema top-level wrapper model."""
    schema = UISchema(
        page="test_page",
        meta={"version": "1.0"},
        components=[
            ComponentSchema(type="div", text="Hello World")
        ]
    )
    data = schema.model_dump()
    assert data["page"] == "test_page"
    assert data["meta"]["version"] == "1.0"
    assert len(data["components"]) == 1


def test_get_viewer_schema():
    """Verify get_viewer_schema helper function."""
    schema = get_viewer_schema("default_project")
    assert schema.page == "viewer"
    assert schema.meta["read_only"] is True
    assert any(c.type == "custom:dashboard-grid" for c in schema.components)


def test_get_etl_editor_schema():
    """Verify get_etl_editor_schema helper function."""
    schema = get_etl_editor_schema()
    assert schema.page == "etl-editor"
    assert any(c.type == "custom:flow-editor" for c in schema.components)


def test_api_ui_schema_endpoint():
    """Test GET /api/ui/schema/{page_name} API endpoint."""
    response = client.get("/api/ui/schema/viewer")
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == "viewer"
    assert "components" in data

    response_etl = client.get("/api/ui/schema/etl-editor")
    assert response_etl.status_code == 200
    data_etl = response_etl.json()
    assert data_etl["page"] == "etl-editor"

    response_fallback = client.get("/api/ui/schema/unknown-page")
    assert response_fallback.status_code == 200
    data_fallback = response_fallback.json()
    assert data_fallback["page"] == "unknown-page"


def test_export_engine_decoupling_headless():
    """Confirm export router endpoints operate headlessly without NiceGUI session objects."""
    response = client.post(
        "/api/projects/test_proj/export",
        json={
            "format": "html",
            "payload": {"title": "Headless Test Export", "widgets": []}
        }
    )
    assert response.status_code == 200
    res_data = response.json()
    assert "export_id" in res_data
    assert res_data["status"] in ["pending", "processing", "completed"]
