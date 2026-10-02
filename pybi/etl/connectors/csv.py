"""CSV data connector using Polars."""

from typing import Any
import polars as pl


def read_csv(filepath: str, **kwargs: Any) -> pl.DataFrame:
    """Read CSV file into a Polars DataFrame.

    Args:
        filepath: Path to the CSV file.
        **kwargs: Additional keyword arguments passed to polars.read_csv.

    Returns:
        pl.DataFrame: The loaded DataFrame.
    """
    return pl.read_csv(filepath, **kwargs)
