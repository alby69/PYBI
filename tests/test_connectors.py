"""Tests for Phase 6 Enterprise Connectors (Snowflake and BigQuery)."""

import polars as pl
import pytest

from pybi.etl.connectors.bigquery import BigQueryConnector
from pybi.etl.connectors.snowflake import SnowflakeConnector


def test_snowflake_connector_lifecycle():
    config = {
        "account": "xy12345.eu-central-1",
        "user": "test_user",
        "password": "secret_password",
        "database": "SALES_DB",
        "schema": "PUBLIC",
    }
    connector = SnowflakeConnector(config)

    assert connector.test_connection() is True
    df = connector.read("fact_sales", limit=10)
    assert isinstance(df, pl.DataFrame)
    assert "snowflake_col" in df.columns
    assert connector.write(df, "fact_sales") is True


def test_bigquery_connector_lifecycle():
    config = {
        "project_id": "my-gcp-project",
        "dataset": "analytics",
        "credentials_path": "/path/to/key.json",
    }
    connector = BigQueryConnector(config)

    assert connector.test_connection() is True
    df = connector.read("daily_metrics", limit=10)
    assert isinstance(df, pl.DataFrame)
    assert "bq_col" in df.columns
    assert connector.write(df, "daily_metrics") is True
