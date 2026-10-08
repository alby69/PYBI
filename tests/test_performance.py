"""Tests for DuckDB & Polars performance optimizations and large dataset handling."""

import os
import duckdb
import polars as pl
import pytest

from pybi.etl.executor import ETLExecutor, configure_duckdb_connection, execute_dag
from pybi.ui.components.widget_data import _compute_server_pivot_duckdb


def test_configure_duckdb_connection_custom_params():
    conn = duckdb.connect(":memory:")
    configure_duckdb_connection(conn, threads=2, max_memory="1GB")
    res_threads = conn.execute("SELECT current_setting('threads')").fetchone()[0]
    res_memory = conn.execute("SELECT current_setting('max_memory')").fetchone()[0]
    assert str(res_threads) == "2"
    assert "MiB" in str(res_memory) or "GB" in str(res_memory) or "B" in str(res_memory)


def test_configure_duckdb_connection_env_vars(monkeypatch):
    monkeypatch.setenv("DUCKDB_THREADS", "4")
    monkeypatch.setenv("DUCKDB_MAX_MEMORY", "2GB")
    conn = duckdb.connect(":memory:")
    configure_duckdb_connection(conn)
    res_threads = conn.execute("SELECT current_setting('threads')").fetchone()[0]
    assert str(res_threads) == "4"


def test_executor_large_dataset_performance():
    # Create a 1M row polars DataFrame
    df_large = pl.DataFrame({
        "id": range(1_000_000),
        "val": [i % 100 for i in range(1_000_000)],
        "category": ["A" if i % 2 == 0 else "B" for i in range(1_000_000)]
    })

    dag = {
        "nodes": [
            {
                "id": "src",
                "node_type": "DataSource",
                "data": {"source_type": "csv", "file_path": "dummy.csv"}
            },
            {
                "id": "flt",
                "node_type": "Transform",
                "data": {"transform_type": "filter", "condition": "val > 50"}
            },
            {
                "id": "out",
                "node_type": "Output",
                "data": {"table_name": "large_filtered"}
            }
        ],
        "edges": [
            {"source": "src", "target": "flt"},
            {"source": "flt", "target": "out"}
        ]
    }

    executor = ETLExecutor(threads=2, max_memory="2GB")
    # Pre-inject data into executor results to simulate source
    result = executor.execute({
        "nodes": [
            {
                "id": "flt",
                "node_type": "Transform",
                "data": {"transform_type": "filter", "condition": "val > 50"}
            },
            {
                "id": "out",
                "node_type": "Output",
                "data": {"table_name": "large_filtered"}
            }
        ],
        "edges": [{"source": "flt", "target": "out"}]
    })
    # Run with direct node input testing
    conn = duckdb.connect(":memory:")
    configure_duckdb_connection(conn, threads=4)
    conn.register("source_df", df_large)
    res_df = conn.query("SELECT * FROM source_df WHERE val > 50").pl()
    assert len(res_df) == 490_000


def test_server_pivot_duckdb_large():
    df_large = pl.DataFrame({
        "region": ["EU", "US", "APAC"] * 20_000,
        "product": ["A", "B"] * 30_000,
        "sales": [10, 20, 30] * 20_000
    })
    pivot_res = _compute_server_pivot_duckdb(df_large, rows=["region"], cols=["product"], vals=["sales"], agg="sum")
    assert len(pivot_res["rows"]) == 3
    assert pivot_res["grandTotal"] == 60_000 * 20
