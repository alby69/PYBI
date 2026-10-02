"""Helpers for rendering Polars DataFrames as NiceGUI tables."""

from typing import Any, Dict, List, Optional, Sequence


def pick_row_key(columns: Sequence[str], rows: Sequence[Dict[str, Any]]) -> Optional[str]:
    """Choose a row key column for a preview table.

    Prefers 'id', then the first column whose values are unique. Returns None
    when no column can safely identify a row, so the table is rendered without
    a row key instead of breaking on missing keys.

    Args:
        columns: DataFrame column names.
        rows: DataFrame rows as dictionaries.

    Returns:
        Optional[str]: Usable row key column name, or None.
    """
    if not columns or not rows:
        return None

    if "id" in columns:
        keys = [row.get("id") for row in rows]
        if all(key is not None for key in keys) and len(set(keys)) == len(keys):
            return "id"

    for column in columns:
        values = [row.get(column) for row in rows]
        if all(value is not None for value in values) and len(set(values)) == len(values):
            return column

    return None


def build_preview_table(df: Any) -> Dict[str, Any]:
    """Build the column and row arguments for a NiceGUI table preview.

    Args:
        df: Polars DataFrame to render.

    Returns:
        Dict[str, Any]: Keyword arguments with 'columns', 'rows' and 'row_key'.
    """
    columns: List[str] = list(df.columns)
    rows: List[Dict[str, Any]] = df.to_dicts()
    table_columns = [{"name": column, "label": column, "field": column, "sortable": True} for column in columns]
    return {
        "columns": table_columns,
        "rows": rows,
        "row_key": pick_row_key(columns, rows),
    }
