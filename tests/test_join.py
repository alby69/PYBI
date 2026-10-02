"""Tests for the Join node: two inputs combined on a key column."""

import os
import tempfile

import polars as pl
import pytest

from pybi.etl.executor import execute_dag
from pybi.etl.node_factory import (
    JOIN_TYPES,
    build_label,
    build_node_data,
    node_kind,
    node_values,
    validate_pipeline,
)


@pytest.fixture
def sales_csv():
    """Sales rows keyed by region."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write("id,region,sales\n")
        f.write("1,EU,1200\n")
        f.write("2,US,450\n")
        f.write("3,EU,300\n")
        f.write("4,APAC,800\n")
    yield f.name
    if os.path.exists(f.name):
        os.remove(f.name)


@pytest.fixture
def regions_csv():
    """Region lookup table."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write("region,region_manager\n")
        f.write("EU,Anna\n")
        f.write("US,Marco\n")
    yield f.name
    if os.path.exists(f.name):
        os.remove(f.name)


def build_dag(sales_csv, regions_csv, **join):
    """Build a pipeline: two CSV sources joined into an output table."""
    join_data = {"node_type": "Transform", "transform_type": "join"}
    join_data.update(join)
    return {
        "nodes": [
            {"id": "s1", "data": {"node_type": "DataSource", "source_type": "csv", "file_path": sales_csv}},
            {"id": "s2", "data": {"node_type": "DataSource", "source_type": "csv", "file_path": regions_csv}},
            {"id": "j1", "data": join_data},
            {"id": "o1", "data": {"node_type": "Output", "table_name": "joined"}},
        ],
        "edges": [
            {"source": "s1", "target": "j1"},
            {"source": "s2", "target": "j1"},
            {"source": "j1", "target": "o1"},
        ],
    }


def test_inner_join_on_same_column(sales_csv, regions_csv):
    """Inner join keeps only the regions present in both inputs."""
    dag = build_dag(sales_csv, regions_csv, how="inner", left_on=["region"], right_on=["region"])
    result = execute_dag(dag)

    assert result.status == "success", result.error
    assert result.output_tables["joined"].height == 3
    assert set(result.output_tables["joined"]["region_manager"]) == {"Anna", "Marco"}
    assert any("INNER joined on region" in line for line in result.logs)


def test_left_join_keeps_unmatched_rows(sales_csv, regions_csv):
    """A left join keeps APAC even though it is missing from the lookup."""
    dag = build_dag(sales_csv, regions_csv, how="left", left_on=["region"], right_on=["region"])
    result = execute_dag(dag)

    assert result.status == "success", result.error
    df = result.output_tables["joined"]
    assert df.height == 4
    assert df.filter(pl.col("region") == "APAC").height == 1


def test_full_join_keeps_both_sides(sales_csv, regions_csv):
    """A full join returns the union of both inputs."""
    dag = build_dag(sales_csv, regions_csv, how="full", left_on=["region"], right_on=["region"])
    result = execute_dag(dag)

    assert result.status == "success", result.error
    assert result.output_tables["joined"].height == 4


def test_join_with_different_key_names(tmp_path):
    """When the two sides name the key differently, both key columns are coalesced."""
    left = tmp_path / "sales.csv"
    left.write_text("id,region,sales\n1,EU,1200\n2,US,450\n")
    right = tmp_path / "regions.csv"
    right.write_text("region_name,region_manager\nEU,Anna\nUS,Marco\n")

    dag = build_dag(str(left), str(right), how="inner", left_on=["region"], right_on=["region_name"])
    result = execute_dag(dag)

    assert result.status == "success", result.error
    df = result.output_tables["joined"]
    assert "region_name" not in df.columns
    assert {"id", "region", "sales", "region_manager"} <= set(df.columns)
    assert df.height == 2


def test_cross_join_needs_no_key(sales_csv, regions_csv):
    """A cross join produces the cartesian product."""
    dag = build_dag(sales_csv, regions_csv, how="cross")
    result = execute_dag(dag)

    assert result.status == "success", result.error
    assert result.output_tables["joined"].height == 4 * 2


def test_composite_key_join(tmp_path):
    """A composite key joins on more than one column."""
    left = tmp_path / "left.csv"
    left.write_text("region,year,sales\nEU,2023,10\nEU,2024,20\nUS,2023,30\n")
    right = tmp_path / "right.csv"
    right.write_text("region_name,year,manager\nEU,2023,Anna\nEU,2024,Anna\nUS,2023,Marco\n")

    dag = build_dag(
        str(left), str(right), how="inner", left_on=["region", "year"], right_on=["region_name", "year"]
    )
    result = execute_dag(dag)

    assert result.status == "success", result.error
    df = result.output_tables["joined"]
    assert df.height == 3
    assert set(df["manager"]) == {"Anna", "Marco"}


def test_join_requires_two_inputs(sales_csv, regions_csv):
    """A join with a single input is rejected with an explanatory error."""
    dag = build_dag(sales_csv, regions_csv, how="inner", left_on=["region"], right_on=["region"])
    dag["edges"] = [edge for edge in dag["edges"] if edge["source"] != "s2"]

    result = execute_dag(dag)

    assert result.status == "error"
    assert "requires two parent inputs" in result.error


def test_join_rejects_unknown_type(sales_csv, regions_csv):
    """An unsupported join type fails validation."""
    dag = build_dag(sales_csv, regions_csv, how="sideways", left_on=["region"], right_on=["region"])
    result = execute_dag(dag)

    assert result.status == "error"
    assert "Unsupported join type" in result.error


def test_join_rejects_mismatched_key_count(sales_csv, regions_csv):
    """Left and right keys must have the same length."""
    dag = build_dag(sales_csv, regions_csv, how="inner", left_on=["region", "id"], right_on=["region"])
    result = execute_dag(dag)

    assert result.status == "error"
    assert "same number of keys" in result.error


def test_join_reports_missing_column(sales_csv, regions_csv):
    """A typo in a key column reports the available columns."""
    dag = build_dag(sales_csv, regions_csv, how="inner", left_on=["regio"], right_on=["region"])
    result = execute_dag(dag)

    assert result.status == "error"
    assert "no column(s) regio" in result.error
    assert "Available columns" in result.error


def test_outer_is_an_alias_of_full(sales_csv, regions_csv):
    """'outer' is accepted and normalised to polars' 'full'."""
    dag = build_dag(sales_csv, regions_csv, how="outer", left_on=["region"], right_on=["region"])
    result = execute_dag(dag)

    assert result.status == "success", result.error
    assert result.output_tables["joined"].height == 4


def test_build_node_data_parses_join():
    """Form values are converted into the executor join payload."""
    data = build_node_data("Join", {"left_on": "region", "right_on": "region", "how": "left"})

    assert data == {
        "node_type": "Transform",
        "transform_type": "join",
        "how": "left",
        "left_on": ["region"],
        "right_on": ["region"],
    }


def test_build_node_data_normalises_outer():
    """'outer' becomes 'full' so the executor only sees polars join types."""
    data = build_node_data("Join", {"left_on": "a", "right_on": "b", "how": "outer"})

    assert data["how"] == "full"
    assert "outer" not in JOIN_TYPES


def test_build_node_data_cross_has_no_keys():
    """A cross join drops the key columns entirely."""
    data = build_node_data("Join", {"left_on": "", "right_on": "", "how": "cross"})

    assert data == {"node_type": "Transform", "transform_type": "join", "how": "cross"}


@pytest.mark.parametrize("values,message", [
    ({"left_on": "", "right_on": "region"}, "Left column is required"),
    ({"left_on": "region", "right_on": ""}, "Right column is required"),
    ({"left_on": "a,b", "right_on": "c"}, "same number of keys"),
    ({"left_on": "a", "right_on": "b", "how": "nope"}, "Unsupported join type"),
])
def test_build_node_data_rejects_invalid(values, message):
    """Invalid join parameters raise a ValueError with a helpful message."""
    with pytest.raises(ValueError, match=message):
        build_node_data("Join", values)


def test_join_node_round_trip():
    """A join node keeps its kind, values and label across an edit."""
    data = build_node_data("Join", {"left_on": "region", "right_on": "region_code", "how": "left"})
    node = {"id": "join_1", "data": data, "label": build_label("Join", data)}

    assert node_kind(node) == "Join"
    values = node_values(node)
    assert values == {"left_on": "region", "right_on": "region_code", "how": "left"}
    assert build_node_data("Join", values) == data


def test_validate_pipeline_requires_two_inputs():
    """A join needs exactly two incoming connections."""
    def problems_for(edges):
        nodes = [
            {"id": "s1", "data": {"node_type": "DataSource", "source_type": "csv", "file_path": "a.csv"}},
            {"id": "s2", "data": {"node_type": "DataSource", "source_type": "csv", "file_path": "b.csv"}},
            {"id": "s3", "data": {"node_type": "DataSource", "source_type": "csv", "file_path": "c.csv"}},
            {"id": "j1", "data": {"node_type": "Transform", "transform_type": "join",
                                  "left_on": ["region"], "right_on": ["region"]}},
        ]
        return validate_pipeline(nodes, edges)

    assert problems_for([
        {"source": "s1", "target": "j1"},
        {"source": "s2", "target": "j1"},
    ]) == []

    one = problems_for([{"source": "s1", "target": "j1"}])
    assert len(one) == 1
    assert "needs two incoming connections" in one[0]

    three = problems_for([
        {"source": "s1", "target": "j1"},
        {"source": "s2", "target": "j1"},
        {"source": "s3", "target": "j1"},
    ])
    assert len(three) == 1
    assert "exactly two incoming connections" in three[0]


def test_build_label_for_cross_join():
    """A cross join label does not mention any key column."""
    label = build_label("Join", {"how": "cross"})

    assert "cross" in label.lower()
    assert "=" not in label