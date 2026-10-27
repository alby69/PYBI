"""Column introspection helpers for the ETL editor.

Reads the schema of the data sources and propagates it along the DAG so the
property panel can offer real column names (instead of free text) for
Select / Group By / Join / Pivot nodes.
"""

import sqlite3
from typing import Any, Dict, List, Optional

import polars as pl

from pybi.etl.connectors import read_csv
from pybi.etl.paths import resolve_data_path

SAMPLE_ROWS = 25


def as_list(value: Any) -> List[str]:
    """Normalise a form value (comma separated string or list) into a list."""
    if value is None:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, (list, tuple)):
        return [str(part).strip() for part in value if str(part).strip()]
    return [str(value).strip()]


def _sqlite_columns(path: str, query_or_table: Optional[str]) -> List[str]:
    """Return the column names of a SQLite query/table without loading rows."""
    conn = sqlite3.connect(path)
    try:
        target = (query_or_table or "").strip()
        if not target:
            tables = [
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
                )
            ]
            if not tables:
                return []
            sql = f'SELECT * FROM "{tables[0]}"'
        elif target.upper().startswith(("SELECT", "WITH", "PRAGMA")):
            sql = target
        else:
            sql = f'SELECT * FROM "{target}"'
        cursor = conn.execute(f"SELECT * FROM ({sql}) LIMIT 1")
        return [description[0] for description in cursor.description or []]
    finally:
        conn.close()


def source_columns(
    source_type: Optional[str],
    file_path: Optional[str],
    csv_separator: Optional[str] = "auto",
    query: Optional[str] = None,
    base_dir: Optional[str] = None,
) -> List[str]:
    """Read the column names of a data source file.

    Only a small sample is read for CSV/SQLite, so opening the property panel
    stays fast even for big files.

    Raises:
        FileNotFoundError: when the file cannot be located.
        ValueError: for unsupported source types.
    """
    if not file_path:
        return []

    kind = (source_type or "csv").lower()
    path = resolve_data_path(file_path, base_dir)

    if kind == "sqlite":
        return [name for name in _sqlite_columns(path, query) if name]
    if kind == "parquet":
        return [name for name in pl.scan_parquet(path).collect_schema().names() if name]
    if kind == "csv":
        frame = read_csv(path, separator=csv_separator or "auto", n_rows=SAMPLE_ROWS)
        return [name for name in frame.columns if name]
    raise ValueError(f"Unsupported source type '{source_type}'.")


class ColumnResolver:
    """Resolve the output columns of each node in a visual DAG."""

    def __init__(
        self,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        base_dir: Optional[str] = None,
    ) -> None:
        """Index the graph so columns can be computed on demand."""
        self.nodes: Dict[str, Dict[str, Any]] = {
            node.get("id"): node for node in nodes or [] if node.get("id")
        }
        self.parents: Dict[str, List[str]] = {node_id: [] for node_id in self.nodes}
        for edge in edges or []:
            source, target = edge.get("source"), edge.get("target")
            if source in self.nodes and target in self.nodes:
                self.parents[target].append(source)
        self.base_dir = base_dir
        self._cache: Dict[str, List[str]] = {}
        self.errors: Dict[str, str] = {}

    def input_columns(self, node_id: str, index: int = 0) -> List[str]:
        """Return the columns produced by the n-th incoming connection."""
        parents = self.parents.get(node_id, [])
        if index >= len(parents):
            return []
        return self.columns(parents[index])

    def input_labels(self, node_id: str) -> List[str]:
        """Return a readable label for each incoming connection."""
        return [
            f"{parent} ({self.nodes[parent].get('label', '')})"
            for parent in self.parents.get(node_id, [])
            if parent in self.nodes
        ]

    def columns(self, node_id: Optional[str]) -> List[str]:
        """Return the columns produced by a node (empty list if unknown)."""
        if not node_id:
            return []
        if node_id in self._cache:
            return self._cache[node_id]
        node = self.nodes.get(node_id)
        if node is None:
            return []

        # Guard against cycles: register an empty result before recursing.
        self._cache[node_id] = []
        try:
            result = self._compute(node, node_id)
        except Exception as err:  # noqa: BLE001 - surface the reason in the panel
            self.errors[node_id] = str(err)
            result = []
        self._cache[node_id] = result
        return result

    # -- per-node computation -------------------------------------------------
    def _compute(self, node: Dict[str, Any], node_id: str) -> List[str]:
        # Local import to avoid a circular import at module load time.
        from pybi.etl.node_factory import node_kind

        kind = node_kind(node)
        data = node.get("data") or {}

        if kind == "DataSource":
            return source_columns(
                data.get("source_type"),
                data.get("file_path") or data.get("path"),
                csv_separator=data.get("csv_separator") or "auto",
                query=data.get("query") or data.get("table_name") or data.get("table"),
                base_dir=self.base_dir,
            )

        if kind == "Filter":
            return self.input_columns(node_id, 0)

        if kind == "Select":
            selected = as_list(data.get("columns"))
            return selected or self.input_columns(node_id, 0)

        if kind == "GroupBy":
            group_by = as_list(data.get("group_by") or data.get("by"))
            aggregations = data.get("aggregations") or {}
            aggregated = list(aggregations) if isinstance(aggregations, dict) else []
            if not group_by and not aggregated:
                return self.input_columns(node_id, 0)
            return group_by + [col for col in aggregated if col not in group_by]

        if kind == "Join":
            left = self.input_columns(node_id, 0)
            right = self.input_columns(node_id, 1)
            # Polars keeps a single copy of same-named key columns.
            return left + [col for col in right if col not in left]

        if kind == "Output":
            return self.input_columns(node_id, 0)

        if kind == "Pivot":
            # Pivot column names depend on the data values, so report the input.
            return self.input_columns(node_id, 0)

        if kind == "AddColumn":
            columns = self.input_columns(node_id, 0)
            new_column = str(data.get("new_column") or data.get("column") or "").strip()
            if new_column and new_column not in columns:
                columns = columns + [new_column]
            return columns

        return self.input_columns(node_id, 0)
