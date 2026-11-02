import os

import duckdb
import polars as pl
import pytest
from fastapi.testclient import TestClient

os.environ["DATA_DIR"] = "pybi_data"

from pybi.api.main import app


@pytest.fixture(scope="session")
def in_memory_duckdb():
    """Provides a fresh in-memory DuckDB connection with sample tables."""
    conn = duckdb.connect(":memory:")
    conn.execute("""
        CREATE TABLE sales AS SELECT
            1 AS id, 'Product A' AS product, 'Electronics' AS category, 100.0 AS price, 2 AS qty, '2026-01-15' AS sale_date
        UNION ALL SELECT
            2, 'Product B', 'Clothing', 45.5, 5, '2026-01-16'
        UNION ALL SELECT
            3, 'Product C', 'Electronics', 250.0, 1, '2026-01-17'
        UNION ALL SELECT
            4, 'Product D', 'Home', 15.0, 10, '2026-01-18'
    """)
    yield conn
    conn.close()


@pytest.fixture
def sample_polars_df():
    """Provides a sample Polars DataFrame for direct transformation testing."""
    return pl.DataFrame({
        "id": [1, 2, 3, 4],
        "product": ["Product A", "Product B", "Product C", "Product D"],
        "category": ["Electronics", "Clothing", "Electronics", "Home"],
        "price": [100.0, 45.5, 250.0, 15.0],
        "qty": [2, 5, 1, 10],
        "sale_date": ["2026-01-15", "2026-01-16", "2026-01-17", "2026-01-18"]
    })


@pytest.fixture
def client():
    """Provides a FastAPI TestClient instance."""
    with TestClient(app) as c:
        yield c
