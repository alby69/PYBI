"""Unit tests for PostgreSQL connector and ETL executor PostgreSQL integration."""

import os
import tempfile
import polars as pl
import pytest

from pybi.etl.connectors.postgres import read_postgres, write_postgres
from pybi.etl.executor import ETLExecutor, execute_dag


@pytest.fixture
def sqlite_test_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    uri = f"sqlite:///{db_path}"
    yield db_path, uri
    if os.path.exists(db_path):
        os.remove(db_path)


def test_postgres_read_write(sqlite_test_db):
    db_path, uri = sqlite_test_db
    df_input = pl.DataFrame({
        "product": ["Widget A", "Widget B"],
        "sales": [100, 250]
    })

    write_postgres(df_input, uri, "sales_report")
    df_output = read_postgres(uri, "sales_report")

    assert len(df_output) == 2
    assert "product" in df_output.columns
    assert "sales" in df_output.columns
    assert df_output["sales"].to_list() == [100, 250]


def test_executor_postgres_nodes(sqlite_test_db):
    db_path, uri = sqlite_test_db

    # Write initial data for postgres source node
    initial_df = pl.DataFrame({
        "item": ["A", "B", "C"],
        "price": [10.0, 20.0, 30.0]
    })
    write_postgres(initial_df, uri, "items_source")

    dag = {
        "nodes": [
            {
                "id": "pg_src",
                "data": {
                    "node_type": "DataSource",
                    "source_type": "postgres",
                    "uri": uri,
                    "query": "SELECT * FROM items_source"
                }
            },
            {
                "id": "filter_1",
                "data": {
                    "node_type": "Transform",
                    "transform_type": "filter",
                    "condition": "price > 15"
                }
            },
            {
                "id": "pg_out",
                "data": {
                    "node_type": "Output",
                    "output_type": "postgres",
                    "uri": uri,
                    "table_name": "items_filtered"
                }
            }
        ],
        "edges": [
            {"id": "e1", "source": "pg_src", "target": "filter_1"},
            {"id": "e2", "source": "filter_1", "target": "pg_out"}
        ]
    }

    result = execute_dag(dag)
    assert result.status == "success"
    assert "pg_out" in result.dataframes
    assert len(result.dataframes["pg_out"]) == 2

    # Verify that data was written to PostgreSQL/SQLAlchemy table
    written_df = read_postgres(uri, "items_filtered")
    assert len(written_df) == 2
    assert written_df["item"].to_list() == ["B", "C"]
