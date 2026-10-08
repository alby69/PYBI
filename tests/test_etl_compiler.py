"""Tests for ETLCompiler query folding engine."""

import pytest
from pybi.etl.compiler import CompilationError, ETLCompiler


def test_compiler_empty_dag():
    compiler = ETLCompiler()
    result = compiler.compile_to_sql({})
    assert result == {}


def test_compiler_simple_dags():
    dag = {
        "nodes": [
            {
                "id": "source_1",
                "data": {
                    "node_type": "DataSource",
                    "source_type": "csv",
                    "file_path": "sales_data.csv",
                },
            },
            {
                "id": "filter_1",
                "data": {
                    "node_type": "Transform",
                    "transform_type": "filter",
                    "condition": "sales > 100",
                },
            },
            {
                "id": "output_1",
                "data": {
                    "node_type": "Output",
                    "table_name": "high_sales",
                },
            },
        ],
        "edges": [
            {"source": "source_1", "target": "filter_1"},
            {"source": "filter_1", "target": "output_1"},
        ],
    }

    compiler = ETLCompiler()
    queries = compiler.compile_to_sql(dag)

    assert "high_sales" in queries
    sql = queries["high_sales"]
    assert "sales_data.csv" in sql
    assert "WHERE sales > 100" in sql
    assert "WITH output_1_cte AS" in sql


def test_compiler_three_node_chain_folding():
    import ibis
    import polars as pl
    from pybi.etl.nodes import FilterNode, GroupByNode, SelectNode
    from pybi.etl.optimizer import SQLOptimizer

    con = ibis.duckdb.connect()
    df = pl.DataFrame({
        "category": ["A", "B", "A", "C", "B"],
        "amount": [100, 200, 150, 300, 250],
        "region": ["North", "North", "South", "East", "West"],
    })
    con.con.register("sales_data", df)
    source_expr = con.table("sales_data")

    dag = [
        FilterNode("f1", column="amount", operator=">", value=100),
        GroupByNode(
            "g1",
            group_cols=["category"],
            agg_col="amount",
            agg_func="sum",
            output_alias="total_amount",
        ),
        SelectNode("s1", columns=["category", "total_amount"]),
    ]

    compiler = ETLCompiler(backend="duckdb", ibis_con=con)
    raw_sql = compiler.compile(dag, source_expr)

    optimizer = SQLOptimizer(dialect="duckdb")
    opt_sql = optimizer.optimize(raw_sql)

    upper_sql = opt_sql.upper()
    assert "WHERE" in upper_sql or "FILTER" in upper_sql
    assert "GROUP BY" in upper_sql
    assert "SELECT" in upper_sql
    assert "CREATE TABLE" not in upper_sql
