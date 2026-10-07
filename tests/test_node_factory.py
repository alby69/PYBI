"""Unit tests for pybi.etl.node_factory node templates and builders."""

import pytest

from pybi.etl.node_factory import (
    AGGREGATIONS,
    NODE_KINDS,
    build_label,
    build_node,
    build_node_data,
    default_values,
    fields_for,
    format_aggregations,
    new_node_id,
    node_kind,
    node_values,
    palette_entry,
    parse_aggregations,
    parse_columns,
    validate_pipeline,
)


def test_every_kind_exposes_a_palette_entry_and_fields():
    for kind, template in NODE_KINDS.items():
        icon, label = palette_entry(kind)
        assert icon == template["icon"]
        assert template["label"] in label
        assert fields_for(kind)
        assert set(default_values(kind)) == {field["key"] for field in fields_for(kind)}


def test_build_data_source_csv():
    data = build_node_data("DataSource", {"source_type": "csv", "file_path": "sales_data.csv", "query": ""})
    assert data == {
        "node_type": "DataSource",
        "source_type": "csv",
        "file_path": "sales_data.csv",
        "csv_separator": "auto",
    }


def test_build_data_source_sqlite_keeps_query():
    data = build_node_data("DataSource", {"source_type": "sqlite", "file_path": "app.db", "query": "SELECT * FROM sales"})
    assert data["query"] == "SELECT * FROM sales"
    assert data["source_type"] == "sqlite"


def test_build_data_source_requires_file_path():
    with pytest.raises(ValueError, match="File path is required"):
        build_node_data("DataSource", {"source_type": "csv", "file_path": "  "})


def test_build_filter_condition():
    data = build_node_data("Filter", {"condition": "region = 'EU'"})
    assert data == {"node_type": "Transform", "transform_type": "filter", "condition": "region = 'EU'"}


def test_build_filter_requires_condition():
    with pytest.raises(ValueError, match="condition is required"):
        build_node_data("Filter", {"condition": ""})


def test_build_select_parses_columns():
    data = build_node_data("Select", {"columns": "region, sales"})
    assert data["transform_type"] == "select"
    assert data["columns"] == ["region", "sales"]


def test_build_groupby_parses_aggregations():
    data = build_node_data("GroupBy", {"group_by": "region", "aggregations": "sales:sum, quantity:sum"})
    assert data["group_by"] == ["region"]
    assert data["aggregations"] == {"sales": "sum", "quantity": "sum"}


def test_build_output_duckdb_has_no_file_path():
    data = build_node_data("Output", {"table_name": "sales_by_region", "output_type": "duckdb", "file_path": "output.db"})
    assert data["table_name"] == "sales_by_region"
    assert data["output_type"] == "duckdb"
    assert "file_path" not in data


def test_build_output_sqlite_keeps_file_path():
    data = build_node_data("Output", {"table_name": "sales", "output_type": "sqlite", "file_path": "warehouse.db"})
    assert data["file_path"] == "warehouse.db"


def test_build_output_requires_table_name():
    with pytest.raises(ValueError, match="Table name is required"):
        build_node_data("Output", {"table_name": ""})


def test_parse_aggregations_roundtrip():
    parsed = parse_aggregations("sales:sum, quantity:mean")
    assert parsed == {"sales": "sum", "quantity": "mean"}
    assert format_aggregations(parsed) == "sales:sum, quantity:mean"
    assert format_aggregations(None) == ""


def test_parse_aggregations_rejects_malformed_pairs():
    with pytest.raises(ValueError, match="Invalid aggregation"):
        parse_aggregations("sales")


def test_parse_aggregations_rejects_unknown_function():
    with pytest.raises(ValueError, match="Unsupported aggregation"):
        parse_aggregations("sales:medianish")


def test_all_supported_aggregations_are_accepted():
    text = ", ".join(f"col_{func}:{func}" for func in AGGREGATIONS)
    assert set(parse_aggregations(text)) == {f"col_{func}" for func in AGGREGATIONS}


def test_parse_columns_ignores_blanks():
    assert parse_columns(" region , sales ,, ") == ["region", "sales"]


def test_build_node_shape_and_label():
    node = build_node("Filter", {"condition": "sales > 300"}, "filter_1", {"x": 20, "y": 40})
    assert node["id"] == "filter_1"
    assert node["position"] == {"x": 20, "y": 40}
    assert node["data"]["node_type"] == "Transform"
    assert "sales > 300" in node["label"]
    assert node["style"]["background"]


def test_build_node_rejects_unknown_kind():
    with pytest.raises(ValueError, match="Unknown node kind"):
        build_node("Nope", {}, "n1", {})


def test_build_label_variants():
    assert "sales_data.csv" in build_label("DataSource", {"source_type": "csv", "file_path": "sales_data.csv"})
    assert "warehouse.db" in build_label("Output", {"table_name": "t", "output_type": "sqlite", "file_path": "warehouse.db"})
    assert "region" in build_label("GroupBy", {"group_by": ["region"], "aggregations": {"sales": "sum"}})


def test_new_node_id_is_unique():
    assert new_node_id("Filter", []) == "filter_1"
    assert new_node_id("Filter", ["filter_1"]) == "filter_2"
    assert new_node_id("Filter", ["filter_1", "filter_3"]) == "filter_2"
    assert new_node_id("Output", ["output_1"]) == "output_2"


def test_node_kind_inference():
    assert node_kind({"data": {"node_type": "DataSource"}}) == "DataSource"
    assert node_kind({"data": {"node_type": "Transform", "transform_type": "filter"}}) == "Filter"
    assert node_kind({"data": {"node_type": "Transform", "transform_type": "select"}}) == "Select"
    assert node_kind({"data": {"node_type": "Transform", "transform_type": "groupby"}}) == "GroupBy"
    assert node_kind({"data": {"node_type": "Output"}}) == "Output"
    assert node_kind({"data": {}}) == "DataSource"


def test_node_values_roundtrip_for_every_kind():
    samples = {
        "DataSource": {"node_type": "DataSource", "source_type": "sqlite", "file_path": "app.db", "query": "SELECT 1"},
        "Filter": {"node_type": "Transform", "transform_type": "filter", "condition": "sales > 1"},
        "Select": {"node_type": "Transform", "transform_type": "select", "columns": ["region", "sales"]},
        "GroupBy": {"node_type": "Transform", "transform_type": "groupby", "group_by": ["region"], "aggregations": {"sales": "sum"}},
        "Output": {"node_type": "Output", "table_name": "t", "output_type": "sqlite", "file_path": "w.db"},
    }
    for expected_kind, data in samples.items():
        node = {"id": "n1", "data": data}
        assert node_kind(node) == expected_kind
        values = node_values(node)
        rebuilt = build_node_data(expected_kind, values)
        for key in ("node_type", "transform_type", "file_path", "condition", "columns", "group_by", "aggregations", "table_name", "query"):
            if key in data:
                assert rebuilt[key] == data[key]


def test_node_values_infers_sqlite_output_from_file_path():
    values = node_values({"data": {"node_type": "Output", "table_name": "t", "file_path": "w.db"}})
    assert values["output_type"] == "sqlite"


def test_validate_pipeline_accepts_linear_chain():
    nodes = [
        build_node("DataSource", {"source_type": "csv", "file_path": "s.csv"}, "source_1", {}),
        build_node("Filter", {"condition": "sales > 1"}, "filter_1", {}),
        build_node("Output", {"table_name": "t", "output_type": "duckdb"}, "output_1", {}),
    ]
    edges = [{"source": "source_1", "target": "filter_1"}, {"source": "filter_1", "target": "output_1"}]
    assert validate_pipeline(nodes, edges) == []


def test_validate_pipeline_flags_empty_graph():
    assert validate_pipeline([], []) == ["The pipeline has no nodes."]


def test_validate_pipeline_flags_transform_without_parent():
    nodes = [build_node("Filter", {"condition": "sales > 1"}, "filter_1", {})]
    assert any("needs at least one incoming connection" in problem for problem in validate_pipeline(nodes, []))


def test_validate_pipeline_flags_source_with_incoming_edge():
    nodes = [
        build_node("DataSource", {"source_type": "csv", "file_path": "s.csv"}, "source_1", {}),
        build_node("Output", {"table_name": "t", "output_type": "duckdb"}, "output_1", {}),
    ]
    edges = [{"source": "output_1", "target": "source_1"}]
    problems = validate_pipeline(nodes, edges)
    assert any("must not have incoming connections" in problem for problem in problems)


def test_validate_pipeline_flags_dangling_edge():
    nodes = [build_node("DataSource", {"source_type": "csv", "file_path": "s.csv"}, "source_1", {})]
    edges = [{"source": "source_1", "target": "ghost"}]
    assert any("missing node" in problem for problem in validate_pipeline(nodes, edges))
