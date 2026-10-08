"""Unit tests for pybi.storage.project_manager module."""

import os
import tempfile
import pytest

import pybi.storage.project_manager as pm
from pybi.core.storage import default_storage


@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    yield db_path
    if os.path.exists(db_path):
        os.remove(db_path)


def test_save_and_load_project(temp_db):
    dag = {"nodes": [{"id": "n1", "label": "CSV Node"}], "edges": []}
    layout = [{"i": "widget_1", "x": 0, "y": 0, "w": 6, "h": 4}]
    bindings = {"widget_1": {"source_name": "sales_df"}}

    result = pm.save_project("test_project", dag=dag, dashboard_layout=layout, bindings=bindings, db_path=temp_db)
    assert result is True

    loaded = pm.load_project("test_project", db_path=temp_db)
    assert loaded["name"] == "test_project"
    assert loaded["dag"] == dag
    assert loaded["dashboard_layout"] == layout
    assert loaded["bindings"] == bindings


def test_update_existing_project(temp_db):
    pm.save_project("proj_v1", dag={"nodes": []}, dashboard_layout=[], bindings={}, db_path=temp_db)

    # Update project
    updated_dag = {"nodes": [{"id": "n1"}]}
    pm.save_project("proj_v1", dag=updated_dag, dashboard_layout=[{"i": "w1"}], bindings={"w1": "src"}, db_path=temp_db)

    loaded = pm.load_project("proj_v1", db_path=temp_db)
    assert loaded["dag"] == updated_dag
    assert len(loaded["dashboard_layout"]) == 1


def test_load_nonexistent_project(temp_db):
    with pytest.raises(FileNotFoundError):
        pm.load_project("non_existent_project", db_path=temp_db)


def test_empty_project_name(temp_db):
    with pytest.raises(ValueError):
        pm.save_project("", db_path=temp_db)

    with pytest.raises(ValueError):
        pm.load_project("   ", db_path=temp_db)


def test_granular_project_manager_api():
    pid = "pm_granular_test"
    default_storage.delete_project(pid)

    # Create project
    proj = pm.create_project(name="Granular Test Project", project_id=pid, description="Test description")
    assert proj["project_id"] == pid
    assert proj["name"] == "Granular Test Project"

    # List projects
    plist = pm.list_projects()
    pids = [p["id"] for p in plist]
    assert pid in pids

    # Get project
    loaded = pm.get_project(pid)
    assert loaded["name"] == "Granular Test Project"

    # Update project
    updated = pm.update_project(pid, name="Updated Granular Name")
    assert updated["name"] == "Updated Granular Name"

    # Save & Load DAG
    sample_dag = {"nodes": [{"id": "n1"}], "edges": []}
    pm.save_dag(pid, sample_dag)
    assert pm.load_dag(pid) == sample_dag

    # Save & Load Dashboard Layout
    sample_layout = [{"i": "w1", "x": 0, "y": 0, "w": 4, "h": 3}]
    pm.save_dashboard_layout(pid, sample_layout, dashboard_id="dash_a", name="Dashboard A")
    dash = pm.load_dashboard_layout(pid, "dash_a")
    assert dash["layout"] == sample_layout

    # Delete Dashboard
    assert pm.delete_dashboard(pid, "dash_a") is True

    # Delete Project
    assert pm.delete_project(pid) is True
