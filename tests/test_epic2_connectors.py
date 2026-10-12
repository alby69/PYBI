"""Tests for Epic 2: Enterprise Connectors & DirectQuery."""

import polars as pl
import pytest

from pybi.etl.connectors.base import BaseConnector
from pybi.etl.connectors.bigquery import BigQueryConnector
from pybi.etl.connectors.snowflake import SnowflakeConnector


class DummyConnector(BaseConnector):
    def test_connection(self) -> bool:
        return True

    def get_schema(self, table_name=None):
        return {"table": table_name or "dummy", "columns": {"id": "Int64"}}

    def read(self, query_or_table, **kwargs):
        return pl.DataFrame({"id": [1, 2]})

    def write(self, df, table_name, if_exists="replace", **kwargs):
        pass

    def direct_query(self, query, **kwargs):
        return pl.DataFrame({"id": [1, 2], "val": ["a", "b"]})


def test_base_connector_interface():
    conn = DummyConnector()
    assert conn.test_connection() is True
    assert conn.get_schema()["table"] == "dummy"
    df_read = conn.read("dummy_table")
    assert len(df_read) == 2
    df_direct = conn.direct_query("SELECT * FROM dummy_table")
    assert df_direct.columns == ["id", "val"]


def test_snowflake_connector_mock():
    sf = SnowflakeConnector(account="xyz123", user="test_user", mock=True)
    assert sf.test_connection() is True
    schema = sf.get_schema("sales")
    assert schema["table"] == "sales"
    assert "columns" in schema

    df = sf.read("sales")
    assert isinstance(df, pl.DataFrame)
    assert len(df) == 3

    df_dq = sf.direct_query("SELECT region, SUM(amount) FROM sales GROUP BY region")
    assert isinstance(df_dq, pl.DataFrame)


def test_bigquery_connector_mock():
    bq = BigQueryConnector(project_id="my-bq-proj", dataset_id="analytics", mock=True)
    assert bq.test_connection() is True
    schema = bq.get_schema("orders")
    assert schema["table"] == "orders"

    df = bq.read("orders")
    assert isinstance(df, pl.DataFrame)
    assert "sales" in df.columns

    df_dq = bq.direct_query("SELECT region, sales FROM orders WHERE sales > 100")
    assert len(df_dq) == 3
