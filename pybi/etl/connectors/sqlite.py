"""SQLite data connector using Python's built-in sqlite3 and Polars."""

import sqlite3
from typing import Any, Optional
import polars as pl


def read_sqlite(
    filepath_or_conn: str,
    query_or_table: Optional[str] = None,
    table_name: Optional[str] = None,
    query: Optional[str] = None,
    **kwargs: Any,
) -> pl.DataFrame:
    """Read a table or query from an SQLite database into a Polars DataFrame.

    Args:
        filepath_or_conn: Filepath to SQLite database file.
        query_or_table: SQL query or table name to query from. If None or empty,
            queries the first user table found in the database.
        table_name: Alternative parameter for table name.
        query: Alternative parameter for SQL query.
        **kwargs: Additional keyword arguments passed to polars.read_database.

    Returns:
        pl.DataFrame: The loaded DataFrame.
    """
    target = query_or_table or query or table_name
    conn = sqlite3.connect(filepath_or_conn)
    try:
        if not target:
            cur = conn.cursor()
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
            )
            tables = [row[0] for row in cur.fetchall()]
            if not tables:
                raise ValueError(
                    f"No user tables found in SQLite database at '{filepath_or_conn}'"
                )
            sql_query = f'SELECT * FROM "{tables[0]}"'
        elif target.strip().upper().startswith(("SELECT", "WITH", "PRAGMA")):
            sql_query = target
        else:
            sql_query = f'SELECT * FROM "{target}"'

        return pl.read_database(sql_query, conn, **kwargs)
    finally:
        conn.close()


def write_sqlite(
    df: pl.DataFrame,
    filepath_or_conn: str,
    table_name: str,
    if_exists: str = "replace",
    **kwargs: Any,
) -> None:
    """Write a Polars DataFrame to a table in an SQLite database.

    Args:
        df: Polars DataFrame to write.
        filepath_or_conn: Filepath to SQLite database file.
        table_name: Target table name.
        if_exists: Strategy if table exists ('replace', 'append', or 'fail').
        **kwargs: Additional keyword arguments.
    """
    conn = sqlite3.connect(filepath_or_conn)
    try:
        cur = conn.cursor()
        if if_exists == "fail":
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?;",
                (table_name,),
            )
            if cur.fetchone():
                raise ValueError(f"Table '{table_name}' already exists in SQLite database.")
        elif if_exists == "replace":
            cur.execute(f'DROP TABLE IF EXISTS "{table_name}"')

        col_defs = []
        for col, dtype in df.schema.items():
            if dtype in (
                pl.Int8,
                pl.Int16,
                pl.Int32,
                pl.Int64,
                pl.UInt8,
                pl.UInt16,
                pl.UInt32,
                pl.UInt64,
                pl.Boolean,
            ):
                sql_type = "INTEGER"
            elif dtype in (pl.Float32, pl.Float64):
                sql_type = "REAL"
            else:
                sql_type = "TEXT"
            col_defs.append(f'"{col}" {sql_type}')

        create_sql = f'CREATE TABLE IF NOT EXISTS "{table_name}" ({", ".join(col_defs)})'
        cur.execute(create_sql)

        if not df.is_empty():
            placeholders = ", ".join(["?"] * len(df.columns))
            insert_sql = f'INSERT INTO "{table_name}" VALUES ({placeholders})'
            cur.executemany(insert_sql, df.rows())

        conn.commit()
    finally:
        conn.close()
