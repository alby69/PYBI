"""Tests for calculated columns (concat / SQL expression) in the ETL editor."""

from pathlib import Path

import polars as pl
import pytest

from pybi.etl.calculated import (
    apply_calculated_column,
    build_calculated_expression,
    quote_identifier,
    quote_literal,
)
from pybi.etl.column_inspector import ColumnResolver
from pybi.etl.executor import execute_dag
from pybi.etl.node_factory import (
    build_label,
    build_node_data,
    node_kind,
    node_values,
    validate_pipeline,
)


def _write_csv(path: Path, rows: list[dict]) -> Path:
    pl.DataFrame(rows).write_csv(path)
    return path


def test_quote_helpers_escape_quotes():
    assert quote_identifier('na"me') == '"na""me"'
    assert quote_literal("O'Brien") == "'O''Brien'"


def test_build_concat_expression_trims_and_joins():
    expr = build_calculated_expression(
        mode="concat",
        columns=["NomeClienteSped", "CittaClienteSped"],
        separator="_",
    )
    assert expr == 'concat_ws(\'_\', trim(CAST("NomeClienteSped" AS VARCHAR)), trim(CAST("CittaClienteSped" AS VARCHAR)))'


def test_build_concat_expression_can_skip_trim():
    expr = build_calculated_expression(mode="concat", columns=["a"], separator="-", trim=False)
    assert expr == 'concat_ws(\'-\', CAST("a" AS VARCHAR))'


def test_build_expression_mode_requires_an_expression():
    with pytest.raises(ValueError, match="espressione SQL"):
        build_calculated_expression(mode="expression", expression="  ")


def test_apply_concat_adds_new_column():
    df = pl.DataFrame({"nome": [" Anna "], "citta": ["Roma"]})

    result = apply_calculated_column(
        df,
        "key_sped",
        mode="concat",
        columns=["nome", "citta"],
        separator="_",
    )

    assert result.columns == ["nome", "citta", "key_sped"]
    assert result["key_sped"].to_list() == ["Anna_Roma"]


def test_apply_expression_replaces_existing_column_at_the_end():
    df = pl.DataFrame({"a": ["x"], "b": ["y"], "key": ["old"]})

    result = apply_calculated_column(
        df,
        "key",
        mode="expression",
        expression='upper("a") || \'-\' || upper("b")',
    )

    assert result.columns == ["a", "b", "key"]
    assert result["key"].to_list() == ["X-Y"]


def test_apply_requires_a_column_name():
    with pytest.raises(ValueError, match="nome della nuova colonna"):
        apply_calculated_column(pl.DataFrame({"a": [1]}), "  ")


def test_node_factory_builds_concat_node():
    data = build_node_data(
        "AddColumn",
        {
            "new_column": "key_sped",
            "mode": "concat",
            "columns": ["NomeClienteSped", "CittaClienteSped"],
            "separator": "_",
            "trim": True,
        },
    )

    assert data == {
        "node_type": "Transform",
        "transform_type": "add_column",
        "new_column": "key_sped",
        "mode": "concat",
        "columns": ["NomeClienteSped", "CittaClienteSped"],
        "separator": "_",
        "trim": True,
    }
    assert node_kind({"data": data}) == "AddColumn"


def test_node_factory_parses_columns_text_and_allows_empty_config():
    data = build_node_data(
        "AddColumn",
        {"new_column": "k", "mode": "concat", "columns": "a, b ,", "separator": "-"},
    )
    assert data["columns"] == ["a", "b"]

    empty = build_node_data("AddColumn", {"new_column": "k", "mode": "concat", "columns": ""})
    assert empty["columns"] == []


def test_validate_pipeline_flags_incomplete_add_column():
    source = {
        "id": "source_1",
        "label": "CSV Source (dati.csv)",
        "data": {"node_type": "DataSource", "source_type": "csv", "file_path": "dati.csv"},
    }
    calc = {
        "id": "calc_1",
        "label": "🧮 Add Column (key)",
        "data": {
            "node_type": "Transform",
            "transform_type": "add_column",
            "new_column": "key",
            "mode": "concat",
            "columns": [],
        },
    }
    problems = validate_pipeline([source, calc], [{"source": "source_1", "target": "calc_1"}])
    assert any("at least one column" in problem for problem in problems)


def test_node_factory_expression_mode_and_roundtrip():
    data = build_node_data(
        "AddColumn",
        {"new_column": "k", "mode": "expression", "expression": 'upper("a")'},
    )
    assert data["expression"] == 'upper("a")'

    values = node_values({"data": data})
    assert values["new_column"] == "k"
    assert values["mode"] == "expression"
    assert values["expression"] == 'upper("a")'
    assert build_node_data("AddColumn", values) == data


def test_node_factory_rejects_invalid_payloads():
    with pytest.raises(ValueError, match="name of the new column"):
        build_node_data("AddColumn", {"new_column": "", "mode": "concat", "columns": "a"})
    with pytest.raises(ValueError, match="SQL expression"):
        build_node_data("AddColumn", {"new_column": "k", "mode": "expression"})
    with pytest.raises(ValueError, match="Unsupported calculated column mode"):
        build_node_data("AddColumn", {"new_column": "k", "mode": "nope"})


def test_build_label_mentions_column_and_sources():
    label = build_label(
        "AddColumn",
        {"new_column": "key_sped", "mode": "concat", "columns": ["a", "b"], "separator": "_"},
    )
    assert "key_sped" in label and "a" in label and "b" in label


def test_validate_pipeline_flags_add_column_without_input():
    node = {
        "id": "calc_1",
        "label": "🧮 Add Column (key)",
        "data": {"node_type": "Transform", "transform_type": "add_column", "new_column": "key"},
    }
    problems = validate_pipeline([node], [])
    assert any("needs at least one incoming connection" in problem for problem in problems)


def _data_source(node_id: str, file_path: str) -> dict:
    return {
        "id": node_id,
        "label": f"CSV Source ({file_path})",
        "data": {"node_type": "DataSource", "source_type": "csv", "file_path": file_path},
    }


def test_resolver_exposes_the_new_column(tmp_path):
    _write_csv(tmp_path / "dati.csv", [{"nome": "Anna", "citta": "Roma"}])
    nodes = [
        _data_source("source_1", "dati.csv"),
        {
            "id": "calc_1",
            "data": {
                "node_type": "Transform",
                "transform_type": "add_column",
                "new_column": "key_sped",
                "mode": "concat",
                "columns": ["nome", "citta"],
                "separator": "_",
            },
        },
        {
            "id": "join_1",
            "data": {"node_type": "Transform", "transform_type": "join", "left_on": ["key_sped"], "right_on": ["key_sped"]},
        },
    ]
    edges = [
        {"source": "source_1", "target": "calc_1"},
        {"source": "calc_1", "target": "join_1"},
    ]

    resolver = ColumnResolver(nodes, edges, base_dir=str(tmp_path))

    assert resolver.input_columns("calc_1", 0) == ["nome", "citta"]
    assert resolver.columns("calc_1") == ["nome", "citta", "key_sped"]
    assert resolver.input_columns("join_1", 0) == ["nome", "citta", "key_sped"]


def test_executor_adds_column_and_uses_it_as_join_key(tmp_path):
    _write_csv(tmp_path / "dati.csv", [{"nome": "Anna ", "citta": "Roma", "qta": 2}])
    _write_csv(tmp_path / "ana.csv", [{"key_sped": "Anna_Roma", "ateco": "1234"}])

    calc_data = build_node_data(
        "AddColumn",
        {"new_column": "key_sped", "mode": "concat", "columns": ["nome", "citta"], "separator": "_"},
    )
    join_data = build_node_data("Join", {"left_on": "key_sped", "right_on": "key_sped", "how": "inner"})

    nodes = [
        _data_source("source_1", "dati.csv"),
        _data_source("source_2", "ana.csv"),
        {"id": "calc_1", "label": "calc", "data": calc_data},
        {"id": "join_1", "label": "join", "data": join_data},
    ]
    edges = [
        {"source": "source_1", "target": "calc_1"},
        {"source": "calc_1", "target": "join_1"},
        {"source": "source_2", "target": "join_1"},
    ]

    result = execute_dag({"nodes": nodes, "edges": edges}, base_dir=str(tmp_path))

    assert result.status == "success", result.error
    calc_df = result.dataframes["calc_1"]
    assert calc_df["key_sped"].to_list() == ["Anna_Roma"]
    joined = result.dataframes["join_1"]
    assert str(joined["ateco"][0]) == "1234"


def test_executor_expression_mode(tmp_path):
    _write_csv(tmp_path / "dati.csv", [{"nome": "anna", "citta": "roma"}])
    nodes = [
        _data_source("source_1", "dati.csv"),
        {
            "id": "calc_1",
            "label": "calc",
            "data": {
                "node_type": "Transform",
                "transform_type": "add_column",
                "new_column": "key_sped",
                "mode": "expression",
                "expression": "upper(nome) || '-' || upper(citta)",
            },
        },
    ]
    edges = [{"source": "source_1", "target": "calc_1"}]

    result = execute_dag({"nodes": nodes, "edges": edges}, base_dir=str(tmp_path))

    assert result.status == "success", result.error
    assert result.dataframes["calc_1"]["key_sped"].to_list() == ["ANNA-ROMA"]
