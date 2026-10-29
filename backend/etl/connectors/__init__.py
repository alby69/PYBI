"""Data connectors package for PyBI ETL."""

from .csv import read_csv
from .parquet import read_parquet
from .postgres import read_postgres, write_postgres
from .sqlite import read_sqlite, write_sqlite
from .writers import write_to_postgres, write_to_sqlite, write_to_duckdb, WriterRegistry

__all__ = [
    "read_csv",
    "read_parquet",
    "read_postgres",
    "write_postgres",
    "read_sqlite",
    "write_sqlite",
    "write_to_postgres",
    "write_to_sqlite",
    "write_to_duckdb",
    "WriterRegistry",
]
