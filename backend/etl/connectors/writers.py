"""Dedicated writer connectors and strategy registry for PyBI ETL output destinations."""

import logging
from typing import Any, Callable, Dict, Tuple
import duckdb
import polars as pl

from .postgres import write_postgres
from .sqlite import write_sqlite

log = logging.getLogger(__name__)


def write_to_postgres(df: pl.DataFrame, uri: str, table_name: str) -> str:
    """Write DataFrame to PostgreSQL database table."""
    write_postgres(df, uri, table_name)
    return f"Saved {len(df)} rows to PostgreSQL table '{table_name}'"


def write_to_sqlite(df: pl.DataFrame, file_path: str, table_name: str) -> str:
    """Write DataFrame to SQLite database file table."""
    if not file_path:
        file_path = "output.db"
    write_sqlite(df, file_path, table_name)
    return f"Saved {len(df)} rows to SQLite table '{table_name}' at '{file_path}'"


def write_to_duckdb(conn: duckdb.DuckDBPyConnection, df: pl.DataFrame, table_name: str) -> str:
    """Register DataFrame in DuckDB connection."""
    conn.register(table_name, df)
    return f"Saved {len(df)} rows to DuckDB table '{table_name}'"


class WriterRegistry:
    """Strategy registry for ETL output destination writers."""

    @classmethod
    def write(
        cls,
        df: pl.DataFrame,
        table_name: str,
        output_type: str,
        filepath_or_uri: str = "",
        duckdb_conn: Any = None,
    ) -> Tuple[str, Tuple[str, pl.DataFrame]]:
        """Write DataFrame to target destination based on output_type.

        Args:
            df: Polars DataFrame to write.
            table_name: Destination table name.
            output_type: Destination type ('duckdb', 'sqlite', 'postgres'/'postgresql').
            filepath_or_uri: Optional file path or connection string/URI.
            duckdb_conn: DuckDB connection instance.

        Returns:
            Tuple[str, Tuple[str, pl.DataFrame]]: (log_message, (table_name, df))
        """
        output_type = (output_type or "duckdb").lower()

        if output_type in ("postgres", "postgresql") or "postgres" in (filepath_or_uri or ""):
            uri = filepath_or_uri
            if not uri:
                raise ValueError(f"No URI provided for PostgreSQL Output table '{table_name}'")
            log_msg = write_to_postgres(df, uri, table_name)
            if duckdb_conn:
                duckdb_conn.register(table_name, df)

        elif output_type == "sqlite" or (filepath_or_uri and any(filepath_or_uri.endswith(ext) for ext in (".sqlite", ".db", ".sqlite3"))):
            fp = filepath_or_uri or "output.db"
            log_msg = write_to_sqlite(df, fp, table_name)
            if duckdb_conn:
                duckdb_conn.register(table_name, df)

        else:
            if duckdb_conn:
                log_msg = write_to_duckdb(duckdb_conn, df, table_name)
            else:
                log_msg = f"Saved {len(df)} rows to DuckDB table '{table_name}'"

        return log_msg, (table_name, df)
