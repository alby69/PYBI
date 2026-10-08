"""Tests for Ibis + SQLGlot Query Folding Engine."""

import ibis
import polars as pl
import pytest

from pybi.etl.compiler import ETLCompiler
from pybi.etl.executor import ETLExecutor
from pybi.etl.nodes import CustomPythonNode, FilterNode, GroupByNode, SelectNode
from pybi.etl.optimizer import SQLOptimizer


def test_query_folding_produces_single_sql():
    """A Filter -> GroupBy chain must compile into ONE SQL query."""
    con = ibis.duckdb.connect()
    df = pl.DataFrame({
        "region": ["North", "South", "North", "East"],
        "amount": [100, 200, 150, 300],
    })
    con.con.register("sales", df)
    source = con.table("sales")

    dag = [
        FilterNode("f1", column="amount", operator=">", value=100),
        GroupByNode(
            "g1",
            group_cols=["region"],
            agg_col="amount",
            agg_func="sum",
            output_alias="total",
        ),
    ]

    compiler = ETLCompiler(backend="duckdb", ibis_con=con)
    sql = compiler.compile(dag, source)

    upper_sql = sql.upper()
    assert "WHERE" in upper_sql or "FILTER" in upper_sql
    assert "GROUP BY" in upper_sql
    assert "SUM" in upper_sql
    assert "CREATE TABLE" not in upper_sql

    optimizer = SQLOptimizer(dialect="duckdb")
    optimized = optimizer.optimize(sql)
    assert "GROUP BY" in optimized.upper()


def test_non_foldable_node_breaks_chain():
    """A CustomPythonNode must trigger materialization boundary without failing."""
    con = ibis.duckdb.connect()
    df = pl.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
    con.con.register("data", df)
    source = con.table("data")

    def double_y(pl_df: pl.DataFrame) -> pl.DataFrame:
        return pl_df.with_columns((pl.col("y") * 2).alias("y"))

    dag = [
        FilterNode("f1", column="x", operator=">", value=1),
        CustomPythonNode("c1", transform_fn=double_y),
        GroupByNode(
            "g1",
            group_cols=["x"],
            agg_col="y",
            agg_func="sum",
            output_alias="total",
        ),
    ]

    compiler = ETLCompiler(backend="duckdb", ibis_con=con)
    sql = compiler.compile(dag, source)
    assert isinstance(sql, str)
    assert len(sql) > 0
    assert "_pybi_tmp_c1_" in sql


def test_sqlglot_optimizer_validates_and_optimizes():
    """Verify SQLOptimizer parses, optimizes, and validates DuckDB SQL."""
    optimizer = SQLOptimizer(dialect="duckdb")
    raw = "SELECT region, SUM(amount) FROM sales WHERE amount > 100 GROUP BY region"

    warnings = optimizer.validate(raw)
    assert len(warnings) == 0

    optimized = optimizer.optimize(raw)
    assert "GROUP BY" in optimized.upper()

    diff = optimizer.explain_diff(raw, optimized)
    assert "Original SQL" in diff
    assert "Optimized SQL" in diff


def test_etl_executor_nodes_end_to_end():
    """Test ETLExecutor.execute_nodes pipeline end-to-end."""
    executor = ETLExecutor()
    source_df = pl.DataFrame({
        "category": ["A", "B", "A", "C", "B"],
        "price": [10, 20, 30, 40, 50],
    })

    dag = [
        FilterNode("f1", column="price", operator=">=", value=20),
        SelectNode("s1", columns=["category", "price"]),
        GroupByNode(
            "g1",
            group_cols=["category"],
            agg_col="price",
            agg_func="sum",
            output_alias="total_price",
        ),
    ]

    result_df, raw_sql, opt_sql = executor.execute_nodes(dag, source_df=source_df)

    assert isinstance(result_df, pl.DataFrame)
    assert len(result_df) == 3  # categories A, B, C
    assert set(result_df["category"].to_list()) == {"A", "B", "C"}
    assert "WHERE" in raw_sql.upper() or "FILTER" in raw_sql.upper()
    assert "GROUP BY" in opt_sql.upper()
