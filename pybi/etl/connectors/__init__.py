"""Data connectors package for PyBI ETL."""

from .csv import read_csv
from .parquet import read_parquet
from .postgres import read_postgres, write_postgres
from .sqlite import read_sqlite, write_sqlite
from .writers import WriterRegistry, write_to_duckdb, write_to_postgres, write_to_sqlite

__all__ = [
    "WriterRegistry",
    "read_csv",
    "read_parquet",
    "read_postgres",
    "read_sqlite",
    "write_postgres",
    "write_sqlite",
    "write_to_duckdb",
    "write_to_postgres",
    "write_to_sqlite",
]
