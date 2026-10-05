"""Tests for project directory storage layout and data file uploads."""

import os
import tempfile
import pytest
from pybi.core.storage import FileProjectStorage


def test_project_directory_structure():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = FileProjectStorage(storage_dir=tmpdir)
        proj_id = "test_proj_dir"

        proj_dir = storage.get_project_dir(proj_id)
        data_dir = storage.get_project_data_dir(proj_id)

        assert os.path.exists(proj_dir)
        assert os.path.exists(data_dir)
        assert data_dir == os.path.join(proj_dir, "data")

        storage.save_project(proj_id, name="Test Project")
        assert storage.project_exists(proj_id)

        loaded = storage.load_project(proj_id)
        assert loaded["name"] == "Test Project"


def test_project_data_file_upload():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = FileProjectStorage(storage_dir=tmpdir)
        proj_id = "test_data_upload"

        dest = storage.save_project_data_file(proj_id, "sample.csv", b"col1,col2\n1,2")
        assert os.path.exists(dest)

        files = storage.list_project_data_files(proj_id)
        assert "sample.csv" in files
