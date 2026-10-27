"""Unit and integration tests for new Power Query ETL transformation nodes."""

import pytest
import polars as pl
from pybi.etl.executor import ETLExecutor, execute_dag
from pybi.etl.nodes.transform import (
    UnpivotNode,
    FillDownNode,
    RenameColumnNode,
    CastColumnNode,
    SplitColumnNode,
    TextTransformNode,
    DeduplicateNode,
    ConditionalColumnNode,
    IndexColumnNode,
)


@pytest.fixture
def sample_df():
    return pl.DataFrame(
        {
            "id": [1, 2, 3, 4],
            "name": [" Alice ", "BOB", "  Charlie  ", "BOB"],
            "category": ["A", None, None, "B"],
            "q1": [10, 20, 30, 40],
            "q2": [100, 200, 300, 400],
            "full_name": ["John Doe", "Jane Smith", "Bob Vance", "Alice Cooper"],
        }
    )


def test_unpivot_node(sample_df):
    node = UnpivotNode("u1", on=["q1", "q2"], index=["id"], variable_name="quarter", value_name="amount")
    res = node.execute(sample_df)
    assert "quarter" in res.columns
    assert "amount" in res.columns
    assert len(res) == 8

    # Test SQL generation
    sql = node.to_sql_expr("source_df")
    assert "UNPIVOT" in sql
    assert "quarter" in sql or "NAME quarter" in sql


def test_fill_down_node(sample_df):
    node = FillDownNode("f1", columns=["category"], order_by="id")
    res = node.execute(sample_df)
    assert res["category"].to_list() == ["A", "A", "A", "B"]

    # Test SQL generation
    sql = node.to_sql_expr("source_df")
    assert "LAST_VALUE" in sql
    assert "IGNORE NULLS" in sql


def test_rename_column_node(sample_df):
    node = RenameColumnNode("r1", mapping={"name": "full_name_clean", "category": "cat"})
    res = node.execute(sample_df)
    assert "full_name_clean" in res.columns
    assert "cat" in res.columns
    assert "name" not in res.columns

    sql = node.to_sql_expr("source_df")
    assert "full_name_clean" in sql


def test_cast_column_node(sample_df):
    node = CastColumnNode("c1", casts={"q1": "double", "id": "text"})
    res = node.execute(sample_df)
    assert res.schema["q1"] == pl.Float64
    assert res.schema["id"] == pl.Utf8

    sql = node.to_sql_expr("source_df")
    assert "CAST(q1 AS DOUBLE)" in sql


def test_split_column_node(sample_df):
    node = SplitColumnNode("s1", column="full_name", delimiter=" ", new_columns=["first_name", "last_name"])
    res = node.execute(sample_df)
    assert "first_name" in res.columns
    assert "last_name" in res.columns
    assert res["first_name"].to_list() == ["John", "Jane", "Bob", "Alice"]

    sql = node.to_sql_expr("source_df")
    assert "STR_SPLIT_PART" in sql


def test_text_transform_node(sample_df):
    node_trim = TextTransformNode("t1", columns=["name"], transform_type="trim")
    res_trim = node_trim.execute(sample_df)
    assert res_trim["name"][0] == "Alice"
    assert res_trim["name"][2] == "Charlie"

    node_lower = TextTransformNode("t2", columns=["name"], transform_type="lower")
    res_lower = node_lower.execute(sample_df)
    assert res_lower["name"][1] == "bob"

    sql = node_trim.to_sql_expr("source_df")
    assert "TRIM(name)" in sql


def test_deduplicate_node(sample_df):
    node = DeduplicateNode("d1", columns=["name"])
    res = node.execute(sample_df)
    assert len(res) == 3  # " Alice ", "BOB", "  Charlie  "

    sql = node.to_sql_expr("source_df")
    assert "ROW_NUMBER() OVER (PARTITION BY name)" in sql


def test_conditional_column_node(sample_df):
    node = ConditionalColumnNode(
        "cc1",
        new_column="tier",
        if_condition="q1 >= 30",
        then_value="High",
        else_value="Low",
    )
    res = node.execute(sample_df)
    assert "tier" in res.columns
    assert res["tier"].to_list() == ["Low", "Low", "High", "High"]

    sql = node.to_sql_expr("source_df")
    assert "CASE WHEN q1 >= 30 THEN 'High' ELSE 'Low' END" in sql


def test_index_column_node(sample_df):
    node = IndexColumnNode("idx1", column_name="idx", start_value=10, increment=5)
    res = node.execute(sample_df)
    assert "idx" in res.columns
    assert res["idx"].to_list() == [10, 15, 20, 25]

    sql = node.to_sql_expr("source_df")
    assert "ROW_NUMBER()" in sql


def test_dag_execution_with_new_transforms(tmp_path):
    csv_file = tmp_path / "data.csv"
    sample = pl.DataFrame(
        {
            "id": [1, 2, 3],
            "category": ["Electronics", None, "Books"],
            "val_q1": [100, 200, 300],
            "val_q2": [150, 250, 350],
        }
    )
    sample.write_csv(csv_file)

    dag = {
        "nodes": [
            {
                "id": "src",
                "data": {
                    "node_type": "DataSource",
                    "source_type": "csv",
                    "file_path": str(csv_file),
                },
            },
            {
                "id": "fill",
                "data": {
                    "node_type": "Transform",
                    "transform_type": "fill_down",
                    "columns": ["category"],
                    "order_by": "id",
                },
            },
            {
                "id": "unpivot",
                "data": {
                    "node_type": "Transform",
                    "transform_type": "unpivot",
                    "on": ["val_q1", "val_q2"],
                    "index": ["id", "category"],
                    "variable_name": "quarter",
                    "value_name": "sales",
                },
            },
            {
                "id": "cond",
                "data": {
                    "node_type": "Transform",
                    "transform_type": "conditional_column",
                    "new_column": "performance",
                    "if_condition": "sales > 200",
                    "then_value": "High",
                    "else_value": "Normal",
                },
            },
            {
                "id": "out",
                "data": {
                    "node_type": "Output",
                    "table_name": "processed_sales",
                },
            },
        ],
        "edges": [
            {"source": "src", "target": "fill"},
            {"source": "fill", "target": "unpivot"},
            {"source": "unpivot", "target": "cond"},
            {"source": "cond", "target": "out"},
        ],
    }

    res = execute_dag(dag)
    assert res.status == "success"
    assert "processed_sales" in res.output_tables
    out_df = res.output_tables["processed_sales"]
    assert "category" in out_df.columns
    assert out_df["category"].to_list().count("Electronics") == 4
    assert "performance" in out_df.columns
