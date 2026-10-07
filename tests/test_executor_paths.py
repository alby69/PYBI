"""Unit tests for DataSource file path resolution in the ETL executor."""

import os
import tempfile

import polars as pl
import pytest

from pybi.etl.executor import execute_dag, resolve_data_path


@pytest.fixture
def project_data_dir():
    """Temporary project data folder containing one CSV file."""
    with tempfile.TemporaryDirectory() as tmp:
        data_dir = os.path.join(tmp, "data")
        os.makedirs(data_dir)
        pl.DataFrame({
            "region": ["EU", "US"],
            "revenue": [10, 20],
        }).write_csv(os.path.join(data_dir, "sales.csv"))
        yield data_dir


def test_bare_filename_resolves_into_project_data_dir(project_data_dir):
    expected = os.path.join(project_data_dir, "sales.csv")
    assert resolve_data_path("sales.csv", project_data_dir) == expected


def test_relative_path_falls_back_to_file_name_in_project_data_dir(project_data_dir):
    expected = os.path.join(project_data_dir, "sales.csv")
    assert resolve_data_path(os.path.join("data", "sales.csv"), project_data_dir) == expected


def test_existing_absolute_path_is_kept(project_data_dir):
    absolute = os.path.join(project_data_dir, "sales.csv")
    assert resolve_data_path(absolute, project_data_dir) == absolute


def test_unknown_file_keeps_user_value(project_data_dir):
    assert resolve_data_path("missing.csv", project_data_dir) == "missing.csv"


def test_no_base_dir_keeps_user_value():
    assert resolve_data_path("sales_data.csv", None) == "sales_data.csv"


def test_cwd_relative_path_is_kept_when_not_in_project_dir(project_data_dir):
    # sales_data.csv lives in the repository root (process working directory)
    assert resolve_data_path("sales_data.csv", project_data_dir) == "sales_data.csv"


def test_execute_dag_reads_uploaded_file_from_project_data_dir(project_data_dir):
    dag = {
        "nodes": [
            {
                "id": "n1",
                "label": "CSV Source (sales.csv)",
                "data": {"node_type": "DataSource", "source_type": "csv", "file_path": "sales.csv"},
            },
            {
                "id": "n2",
                "label": "DuckDB Table (eu_sales)",
                "data": {"node_type": "Output", "table_name": "eu_sales"},
            },
        ],
        "edges": [{"id": "e1", "source": "n1", "target": "n2"}],
    }

    result = execute_dag(dag, base_dir=project_data_dir)

    assert result.status == "success"
    assert "eu_sales" in result.output_tables
    assert len(result.output_tables["eu_sales"]) == 2
    assert any(os.path.join(project_data_dir, "sales.csv") in log for log in result.logs)


def test_execute_dag_without_base_dir_still_reads_known_paths(project_data_dir):
    dag = {
        "nodes": [
            {
                "id": "n1",
                "data": {"node_type": "DataSource", "source_type": "csv", "file_path": "sales_data.csv"},
            },
        ],
        "edges": [],
    }

    result = execute_dag(dag)

    assert result.status == "success"
    assert "n1" in result.dataframes
