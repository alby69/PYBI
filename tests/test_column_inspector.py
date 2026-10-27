"""Unit tests for pybi.etl.column_inspector column introspection helpers."""

from pathlib import Path

import polars as pl
import pytest

from pybi.etl.column_inspector import ColumnResolver, as_list, source_columns


def _write_csv(path: Path, rows: list[dict]) -> Path:
    pl.DataFrame(rows).write_csv(path)
    return path


def test_as_list_accepts_strings_and_lists():
    assert as_list("region, sales ,") == ["region", "sales"]
    assert as_list(["a", " b "]) == ["a", "b"]
    assert as_list(None) == []


def test_source_columns_reads_csv_header(tmp_path):
    csv_path = _write_csv(tmp_path / "sales.csv", [{"region": "EU", "sales": 10}])

    assert source_columns("csv", str(csv_path)) == ["region", "sales"]


def test_source_columns_resolves_relative_path_against_base_dir(tmp_path):
    _write_csv(tmp_path / "sales.csv", [{"region": "EU", "sales": 10}])

    assert source_columns("csv", "sales.csv", base_dir=str(tmp_path)) == ["region", "sales"]


def test_source_columns_detects_semicolon_separator(tmp_path):
    csv_path = tmp_path / "sales.csv"
    csv_path.write_text("region;amount\nEU;1,5\n", encoding="utf-8")

    assert source_columns("csv", str(csv_path), csv_separator="auto") == ["region", "amount"]


def test_source_columns_without_file_returns_empty():
    assert source_columns("csv", "") == []


def test_source_columns_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        source_columns("csv", str(tmp_path / "missing.csv"))


def _data_source(node_id: str, file_path: str) -> dict:
    return {
        "id": node_id,
        "label": f"CSV Source ({file_path})",
        "data": {"node_type": "DataSource", "source_type": "csv", "file_path": file_path},
    }


def test_resolver_propagates_columns_through_transforms(tmp_path):
    _write_csv(tmp_path / "sales.csv", [{"region": "EU", "sales": 10, "product": "A"}])
    nodes = [
        _data_source("source_1", "sales.csv"),
        {
            "id": "select_1",
            "data": {"node_type": "Transform", "transform_type": "select", "columns": ["region", "sales"]},
        },
        {
            "id": "group_1",
            "data": {
                "node_type": "Transform",
                "transform_type": "groupby",
                "group_by": ["region"],
                "aggregations": {"sales": "sum"},
            },
        },
    ]
    edges = [
        {"source": "source_1", "target": "select_1"},
        {"source": "select_1", "target": "group_1"},
    ]

    resolver = ColumnResolver(nodes, edges, base_dir=str(tmp_path))

    assert resolver.columns("source_1") == ["region", "sales", "product"]
    assert resolver.columns("select_1") == ["region", "sales"]
    assert resolver.columns("group_1") == ["region", "sales"]


def test_resolver_exposes_left_and_right_join_inputs(tmp_path):
    _write_csv(tmp_path / "sales.csv", [{"region": "EU", "sales": 10}])
    _write_csv(tmp_path / "targets.csv", [{"region": "EU", "target": 20}])
    nodes = [
        _data_source("source_1", "sales.csv"),
        _data_source("source_2", "targets.csv"),
        {
            "id": "join_1",
            "data": {
                "node_type": "Transform",
                "transform_type": "join",
                "how": "inner",
                "left_on": ["region"],
                "right_on": ["region"],
            },
        },
    ]
    edges = [
        {"source": "source_1", "target": "join_1"},
        {"source": "source_2", "target": "join_1"},
    ]

    resolver = ColumnResolver(nodes, edges, base_dir=str(tmp_path))

    assert resolver.input_columns("join_1", 0) == ["region", "sales"]
    assert resolver.input_columns("join_1", 1) == ["region", "target"]
    assert resolver.columns("join_1") == ["region", "sales", "target"]


def test_resolver_reports_errors_instead_of_raising(tmp_path):
    nodes = [_data_source("source_1", "missing.csv")]
    resolver = ColumnResolver(nodes, [], base_dir=str(tmp_path))

    assert resolver.columns("source_1") == []
    assert "missing.csv" in resolver.errors["source_1"]
