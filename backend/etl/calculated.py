"""Helpers to add calculated (derived) columns to a DataFrame with DuckDB.

The ETL editor exposes two ways to build a new column:

* ``concat`` — join two or more text columns with a separator
  (``NomeClienteSped + "_" + CittaClienteSped``);
* ``expression`` — a free DuckDB SQL expression
  (``upper("NomeClienteSped") || '_' || "CittaClienteSped"``).

Both the executor and the live preview in the property panel use the helpers
below, so what you see in the panel is exactly what the pipeline computes.
"""

from typing import Any, Iterable, List, Optional

import duckdb
import polars as pl

CALCULATED_MODES = ("concat", "expression")


def quote_identifier(name: str) -> str:
    """Quote a column identifier for DuckDB (handles spaces and quotes)."""
    return '"' + str(name).replace('"', '""') + '"'


def quote_literal(value: Any) -> str:
    """Quote a string literal for DuckDB."""
    return "'" + str(value).replace("'", "''") + "'"


def _clean_columns(columns: Optional[Iterable[str]]) -> List[str]:
    if not columns:
        return []
    if isinstance(columns, str):
        columns = columns.split(",")
    return [str(column).strip() for column in columns if str(column).strip()]


def build_calculated_expression(
    mode: str = "concat",
    columns: Optional[Iterable[str]] = None,
    separator: str = "_",
    expression: Optional[str] = None,
    trim: bool = True,
) -> str:
    """Build the SQL expression that computes the calculated column.

    Raises:
        ValueError: when the configuration is incomplete.
    """
    mode = (mode or "concat").lower()
    if mode == "expression":
        expr = (expression or "").strip()
        if not expr:
            raise ValueError("Una espressione SQL è obbligatoria per il campo calcolato.")
        return expr

    cols = _clean_columns(columns)
    if not cols:
        raise ValueError("Seleziona almeno una colonna da concatenare.")

    separator = "_" if separator is None else str(separator)
    parts = []
    for column in cols:
        ident = quote_identifier(column)
        parts.append(f"trim(CAST({ident} AS VARCHAR))" if trim else f"CAST({ident} AS VARCHAR)")
    args = ", ".join([quote_literal(separator)] + parts)
    return f"concat_ws({args})"


def describe_calculated_column(
    mode: str = "concat",
    columns: Optional[Iterable[str]] = None,
    separator: str = "_",
    expression: Optional[str] = None,
    trim: bool = True,
) -> str:
    """Return the SQL expression shown in the property panel (raises on errors)."""
    return build_calculated_expression(
        mode=mode,
        columns=columns,
        separator=separator,
        expression=expression,
        trim=trim,
    )


def apply_calculated_column(
    df: pl.DataFrame,
    new_column: str,
    mode: str = "concat",
    columns: Optional[Iterable[str]] = None,
    separator: str = "_",
    expression: Optional[str] = None,
    trim: bool = True,
) -> pl.DataFrame:
    """Return a copy of ``df`` with the calculated column added (or replaced)."""
    target = (new_column or "").strip()
    if not target:
        raise ValueError("Il nome della nuova colonna è obbligatorio.")

    expr = build_calculated_expression(
        mode=mode,
        columns=columns,
        separator=separator,
        expression=expression,
        trim=trim,
    )

    # Keep the existing column order and put the calculated column at the end.
    existing = [column for column in df.columns if column != target]
    projection = ", ".join(quote_identifier(column) for column in existing)
    alias = f"{expr} AS {quote_identifier(target)}"
    projection = f"{projection}, {alias}" if projection else alias

    con = duckdb.connect()
    try:
        con.register("source_df", df)
        return con.query(f"SELECT {projection} FROM source_df").pl()
    finally:
        con.close()
