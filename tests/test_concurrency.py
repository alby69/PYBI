"""Tests for request-scoped concurrency and caching in PyBI."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
import pytest
import polars as pl
from pybi.core.storage import default_storage
from pybi.etl.executor import ETLExecutor


def test_storage_caching():
    project_id = "test_cache_project"
    cache_key = "abc123hash"

    df = pl.DataFrame({"col1": [1, 2, 3], "col2": ["x", "y", "z"]})

    cached_file = default_storage.save_cached_table(project_id, cache_key, df)
    assert cached_file.endswith(".parquet")

    loaded_df = default_storage.get_cached_table(project_id, cache_key)
    assert loaded_df is not None
    assert loaded_df.shape == (3, 2)
    assert loaded_df["col1"].to_list() == [1, 2, 3]


def test_concurrency_no_duckdb_locks():
    """Simulate 10 concurrent ETLExecutor query requests to ensure no Database is locked error occurs."""
    def run_query(i: int):
        executor = ETLExecutor()
        df = pl.DataFrame({"a": [i, i + 1], "b": [i * 10, (i + 1) * 10]})
        res, raw_sql, opt_sql = executor.execute_nodes(
            dag=[],
            source_df=df,
            source_table_name=f"test_tbl_{i}",
        )
        return res.height

    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = [pool.submit(run_query, i) for i in range(10)]
        results = [f.result() for f in futures]

    assert len(results) == 10
    assert all(r == 2 for r in results)
