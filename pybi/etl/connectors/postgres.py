"""PostgreSQL data connector using SQLAlchemy and Polars."""

from typing import Any, Optional, Union
import polars as pl
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


def read_postgres(
    uri_or_engine: Union[str, Engine],
    query: str,
    **kwargs: Any,
) -> pl.DataFrame:
    """Read a query or table from a PostgreSQL database into a Polars DataFrame using SQLAlchemy.

    Args:
        uri_or_engine: PostgreSQL connection URI string or SQLAlchemy Engine.
        query: SQL query or table name to execute/read.
        **kwargs: Additional keyword arguments passed to polars.read_database.

    Returns:
        pl.DataFrame: The loaded DataFrame.
    """
    if isinstance(uri_or_engine, str):
        if not uri_or_engine or not uri_or_engine.strip():
            raise ValueError("PostgreSQL connection URI cannot be empty.")
        engine = create_engine(uri_or_engine)
        should_dispose = True
    else:
        engine = uri_or_engine
        should_dispose = False

    if not query or not query.strip():
        raise ValueError("PostgreSQL query or table name cannot be empty.")

    clean_query = query.strip()
    if not clean_query.upper().startswith(("SELECT", "WITH", "PRAGMA", "EXPLAIN")):
        clean_query = f'SELECT * FROM "{clean_query}"'

    try:
        return pl.read_database(query=clean_query, connection=engine, **kwargs)
    finally:
        if should_dispose:
            engine.dispose()


def write_postgres(
    df: pl.DataFrame,
    uri_or_engine: Union[str, Engine],
    table_name: str,
    if_exists: str = "replace",
    **kwargs: Any,
) -> None:
    """Write a Polars DataFrame to a table in a PostgreSQL database using SQLAlchemy.

    Args:
        df: Polars DataFrame to write.
        uri_or_engine: PostgreSQL connection URI string or SQLAlchemy Engine.
        table_name: Target table name.
        if_exists: Table exist behavior ('replace', 'append', or 'fail').
        **kwargs: Additional keyword arguments.
    """
    if isinstance(uri_or_engine, str):
        if not uri_or_engine or not uri_or_engine.strip():
            raise ValueError("PostgreSQL connection URI cannot be empty.")
        engine = create_engine(uri_or_engine)
        should_dispose = True
    else:
        engine = uri_or_engine
        should_dispose = False

    if not table_name or not table_name.strip():
        raise ValueError("Target table name cannot be empty.")

    try:
        # Map if_exists to polars write_database if_table_exists parameter
        if_table_exists = if_exists.lower()
        if if_table_exists == "replace":
            mode = "replace"
        elif if_table_exists == "append":
            mode = "append"
        else:
            mode = "fail"

        df.write_database(
            table_name=table_name.strip(),
            connection=engine,
            if_table_exists=mode,
            **kwargs,
        )
    finally:
        if should_dispose:
            engine.dispose()


if __name__ == "__main__":
    import os
    print("Testing pybi/etl/connectors/postgres.py standalone...")
    test_db_file = "test_postgres_connector.db"
    if os.path.exists(test_db_file):
        os.remove(test_db_file)

    test_uri = f"sqlite:///{test_db_file}"
    df_sample = pl.DataFrame({"id": [1, 2], "name": ["Alice", "Bob"]})

    write_postgres(df_sample, test_uri, "users")
    print("Written sample df to table 'users'")

    df_read = read_postgres(test_uri, "SELECT * FROM users")
    print("Read sample df from table 'users':\n", df_read)

    assert len(df_read) == 2
    assert df_read.columns == ["id", "name"]

    if os.path.exists(test_db_file):
        os.remove(test_db_file)
    print("pybi/etl/connectors/postgres.py self-test passed!")
