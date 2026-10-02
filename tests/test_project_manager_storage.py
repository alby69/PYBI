"""Unit tests for SQLite-backed pybi.storage.project_manager module."""

import os
import tempfile
import pytest

from pybi.storage.project_manager import load_project, save_project


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

    result = save_project("test_project", dag=dag, dashboard_layout=layout, bindings=bindings, db_path=temp_db)
    assert result is True

    loaded = load_project("test_project", db_path=temp_db)
    assert loaded["name"] == "test_project"
    assert loaded["dag"] == dag
    assert loaded["dashboard_layout"] == layout
    assert loaded["bindings"] == bindings


def test_update_existing_project(temp_db):
    save_project("proj_v1", dag={"nodes": []}, dashboard_layout=[], bindings={}, db_path=temp_db)

    # Update project
    updated_dag = {"nodes": [{"id": "n1"}]}
    save_project("proj_v1", dag=updated_dag, dashboard_layout=[{"i": "w1"}], bindings={"w1": "src"}, db_path=temp_db)

    loaded = load_project("proj_v1", db_path=temp_db)
    assert loaded["dag"] == updated_dag
    assert len(loaded["dashboard_layout"]) == 1


def test_load_nonexistent_project(temp_db):
    with pytest.raises(FileNotFoundError):
        load_project("non_existent_project", db_path=temp_db)


def test_empty_project_name(temp_db):
    with pytest.raises(ValueError):
        save_project("", db_path=temp_db)

    with pytest.raises(ValueError):
        load_project("   ", db_path=temp_db)
