"""Parquet data connector using Polars."""

from typing import Any
import polars as pl


def read_parquet(filepath: str, **kwargs: Any) -> pl.DataFrame:
    """Read Parquet file into a Polars DataFrame.

    Args:
        filepath: Path to the Parquet file.
        **kwargs: Additional keyword arguments passed to polars.read_parquet.

    Returns:
        pl.DataFrame: The loaded DataFrame.
    """
    return pl.read_parquet(filepath, **kwargs)
