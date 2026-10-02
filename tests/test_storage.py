"""Unit tests for pybi.core.storage module."""

import os
import tempfile
import pytest

from pybi.core.storage import FileProjectStorage


@pytest.fixture
def temp_storage():
    """Fixture providing a FileProjectStorage instance in a temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = FileProjectStorage(storage_dir=tmpdir)
        yield storage


def test_save_and_load_project(temp_storage):
    """Test saving and loading full project data."""
    dag = {
        "nodes": [{"id": "n1", "label": "Source"}],
        "edges": []
    }
    layout = [
        {"i": "w1", "x": 0, "y": 0, "w": 4, "h": 3}
    ]

    saved = temp_storage.save_project(
        project_id="test_proj",
        etl_dag=dag,
        dashboard_layout=layout,
        name="Test Project"
    )

    assert saved["project_id"] == "test_proj"
    assert saved["name"] == "Test Project"
    assert saved["etl_dag"] == dag
    assert saved["dashboard_layout"] == layout
    assert "created_at" in saved
    assert "updated_at" in saved

    loaded = temp_storage.load_project("test_proj")
    assert loaded["project_id"] == "test_proj"
    assert loaded["name"] == "Test Project"
    assert loaded["etl_dag"] == dag
    assert loaded["dashboard_layout"] == layout


def test_list_and_delete_projects(temp_storage):
    """Test listing and deleting project configurations."""
    temp_storage.save_project("proj1", name="Project 1")
    temp_storage.save_project("proj2", name="Project 2")

    projects = temp_storage.list_projects()
    assert "proj1" in projects
    assert "proj2" in projects

    deleted = temp_storage.delete_project("proj1")
    assert deleted is True

    projects_after = temp_storage.list_projects()
    assert "proj1" not in projects_after
    assert "proj2" in projects_after


def test_partial_updates(temp_storage):
    """Test updating ETL DAG and Dashboard layout independently."""
    dag1 = {"nodes": [{"id": "a"}], "edges": []}
    temp_storage.save_etl_dag("proj_partial", dag1)

    loaded_dag1 = temp_storage.load_etl_dag("proj_partial")
    assert loaded_dag1 == dag1

    layout1 = [{"i": "w1", "x": 1, "y": 1, "w": 2, "h": 2}]
    temp_storage.save_dashboard_layout("proj_partial", layout1)

    loaded_layout1 = temp_storage.load_dashboard_layout("proj_partial")
    assert loaded_layout1 == layout1

    # Check DAG was retained after updating layout
    reloaded = temp_storage.load_project("proj_partial")
    assert reloaded["etl_dag"] == dag1
    assert reloaded["dashboard_layout"] == layout1
