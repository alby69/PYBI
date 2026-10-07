"""Unit tests for pybi.core.storage module."""

import os
import tempfile
import pytest

from pybi.core.storage import (
    FileProjectStorage,
    resolve_storage_dir,
    sanitize_project_id,
)


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


def test_load_dashboard_layout_distinguishes_never_saved_from_empty(temp_storage):
    """A project that never saved a layout reports None; a saved empty list reports []."""
    with pytest.raises(FileNotFoundError):
        temp_storage.load_dashboard_layout("never_saved")

    temp_storage.save_project("no_layout", name="No Layout")
    assert temp_storage.load_dashboard_layout("no_layout") is None

    # ETL-only saves must not fabricate a dashboard layout
    temp_storage.save_etl_dag("etl_only", {"nodes": [], "edges": []})
    assert temp_storage.load_dashboard_layout("etl_only") is None

    temp_storage.save_dashboard_layout("etl_only", [])
    assert temp_storage.load_dashboard_layout("etl_only") == []

    layout = [{"i": "w1", "x": 0, "y": 0, "w": 4, "h": 3}]
    temp_storage.save_dashboard_layout("etl_only", layout)
    assert temp_storage.load_dashboard_layout("etl_only") == layout

    # An ETL-only update must preserve the previously saved layout
    temp_storage.save_etl_dag("etl_only", {"nodes": [{"id": "a"}], "edges": []})
    assert temp_storage.load_dashboard_layout("etl_only") == layout


def test_sanitize_project_id():
    assert sanitize_project_id("my project") == "myproject"
    assert sanitize_project_id("sales-2024_q1") == "sales-2024_q1"
    assert sanitize_project_id("../escape") == "escape"
    assert sanitize_project_id("") == "default"
    assert sanitize_project_id("!!!") == "default"


def test_resolve_storage_dir_prefers_explicit_argument(monkeypatch):
    monkeypatch.setenv("DATA_DIR", "/app/data")
    assert resolve_storage_dir("/explicit") == "/explicit"


def test_resolve_storage_dir_uses_data_dir(monkeypatch):
    monkeypatch.setenv("DATA_DIR", "/app/data")
    assert resolve_storage_dir() == "/app/data"


def test_resolve_storage_dir_falls_back_to_default(monkeypatch):
    monkeypatch.delenv("DATA_DIR", raising=False)
    assert resolve_storage_dir() == "pybi_data"


def test_storage_uses_data_dir_env(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("DATA_DIR", tmpdir)
        storage = FileProjectStorage()
        assert storage.storage_dir == tmpdir
        assert storage.projects_dir == os.path.join(tmpdir, "projects")
        storage.save_project("env_proj", name="Env Project")
        assert os.path.exists(os.path.join(tmpdir, "projects", "env_proj.json"))
        assert storage.load_project("env_proj")["name"] == "Env Project"


def test_project_exists(temp_storage):
    assert temp_storage.project_exists("later") is False
    temp_storage.save_project("later")
    assert temp_storage.project_exists("later") is True


def test_rename_project_preserves_content(temp_storage):
    dag = {"nodes": [{"id": "n1"}], "edges": []}
    layout = [{"i": "w1", "x": 0, "y": 0, "w": 4, "h": 3}]
    temp_storage.save_project("old_id", etl_dag=dag, dashboard_layout=layout, name="Old Name")

    new_id = temp_storage.rename_project("old_id", "new_id")

    assert new_id == "new_id"
    assert temp_storage.project_exists("old_id") is False
    renamed = temp_storage.load_project("new_id")
    assert renamed["etl_dag"] == dag
    assert renamed["dashboard_layout"] == layout
    assert renamed["name"] == "Old Name"
    assert renamed["created_at"]


def test_rename_project_can_change_name(temp_storage):
    temp_storage.save_project("keep", name="Keep")
    temp_storage.rename_project("keep", "renamed", name="Brand New")
    assert temp_storage.load_project("renamed")["name"] == "Brand New"


def test_rename_project_to_same_id_just_updates_name(temp_storage):
    temp_storage.save_project("same", etl_dag={"nodes": [{"id": "a"}], "edges": []}, name="Before")
    temp_storage.rename_project("same", "same", name="After")
    assert temp_storage.load_project("same")["name"] == "After"
    assert temp_storage.load_project("same")["etl_dag"] == {"nodes": [{"id": "a"}], "edges": []}


def test_rename_project_rejects_existing_target(temp_storage):
    temp_storage.save_project("taken")
    temp_storage.save_project("mover")
    with pytest.raises(ValueError, match="already exists"):
        temp_storage.rename_project("mover", "taken")
    assert temp_storage.project_exists("mover") is True


def test_rename_project_requires_source(temp_storage):
    with pytest.raises(FileNotFoundError):
        temp_storage.rename_project("ghost", "target")


def test_delete_project_returns_false_when_missing(temp_storage):
    assert temp_storage.delete_project("never_saved") is False


def test_project_data_directory_and_file_operations(temp_storage):
    pid = "test_data_proj"

    # Test get_project_data_dir creates data directory
    data_dir = temp_storage.get_project_data_dir(pid)
    assert os.path.exists(data_dir)
    assert os.path.isdir(data_dir)
    assert data_dir.endswith(os.path.join("test_data_proj", "data"))

    # Test saving project creates data directory automatically
    temp_storage.save_project(pid, name="Data Test Project")
    assert os.path.exists(data_dir)

    # Test saving uploaded file
    file_content = b"id,val\n1,100\n2,200\n"
    file_path = temp_storage.save_uploaded_file(pid, "sales.csv", file_content)
    assert os.path.exists(file_path)
    with open(file_path, "rb") as f:
        assert f.read() == file_content

    # Test listing files
    files = temp_storage.list_project_files(pid)
    assert files == ["sales.csv"]

    # Test deleting file
    deleted_file = temp_storage.delete_project_file(pid, "sales.csv")
    assert deleted_file is True
    assert temp_storage.list_project_files(pid) == []
    assert temp_storage.delete_project_file(pid, "sales.csv") is False

    # Test deleting project cleans project directory and json
    temp_storage.save_uploaded_file(pid, "extra.parquet", b"dummy")
    project_dir = os.path.dirname(data_dir)
    assert os.path.exists(project_dir)

    deleted_proj = temp_storage.delete_project(pid)
    assert deleted_proj is True
    assert not os.path.exists(project_dir)
    assert not temp_storage.project_exists(pid)
