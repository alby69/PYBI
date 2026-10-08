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
