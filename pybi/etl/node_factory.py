"""Declarative ETL node templates, builders and parsers for the DAG editor.

This module acts as a facade over UI schema definitions (pybi.etl.nodes.ui_schema)
and node class registries (pybi.etl.nodes.registry).
"""

from typing import Any

from pybi.etl.nodes.registry import NODE_REGISTRY, get_node_class
from pybi.etl.nodes.ui_schema import (
    _TRANSFORM_KIND,
    AGGREGATIONS,
    JOIN_TYPES,
    KIND_PREFIX,
    NODE_KINDS,
    OUTPUT_TYPES,
    PIVOT_STYLE,
    SOURCE_TYPES,
    TRANSFORM_TYPES,
    build_label,
    build_node,
    build_node_data,
    default_values,
    fields_for,
    new_node_id,
    node_kind,
    node_values,
    palette_entry,
)


def parse_aggregations(text: str) -> dict[str, str]:
    """Parse an aggregation text field into a column/function mapping."""
    result: dict[str, str] = {}
    for chunk in text.split(","):
        pair = chunk.strip()
        if not pair:
            continue
        if ":" not in pair:
            raise ValueError(f"Invalid aggregation '{pair}'. Expected 'column:function', e.g. 'sales:sum'.")
        column, func = (part.strip() for part in pair.split(":", 1))
        if not column or not func:
            raise ValueError(f"Invalid aggregation '{pair}'. Expected 'column:function', e.g. 'sales:sum'.")
        if func not in AGGREGATIONS:
            raise ValueError(f"Unsupported aggregation '{func}'. Supported: {', '.join(AGGREGATIONS)}.")
        result[column] = func
    return result


def format_aggregations(aggregations: dict[str, str] | None) -> str:
    """Render an aggregation mapping back to its text field representation."""
    if not aggregations:
        return ""
    return ", ".join(f"{column}:{func}" for column, func in aggregations.items())


def parse_columns(text: str) -> list[str]:
    """Parse a comma separated column list."""
    return [chunk.strip() for chunk in text.split(",") if chunk.strip()]


def validate_pipeline(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> list[str]:
    """Check a pipeline before execution and return human readable problems."""
    problems: list[str] = []
    if not nodes:
        return ["The pipeline has no nodes."]

    ids = {node.get("id") for node in nodes}
    parents: dict[str, list[str]] = {node_id: [] for node_id in ids}
    for edge in edges:
        source, target = edge.get("source"), edge.get("target")
        if source not in ids or target not in ids:
            problems.append(f"Edge {source} -> {target} references a missing node.")
            continue
        parents[target].append(source)

    for node in nodes:
        kind = node_kind(node)
        node_id = node.get("id", "unknown")
        if kind in ("Filter", "Select", "GroupBy", "Pivot", "Output") and not parents[node_id]:
            problems.append(f"Node '{node_id}' ({kind}) needs at least one incoming connection.")
        if kind in ("DataSource",) and parents[node_id]:
            problems.append(f"Node '{node_id}' (Data Source) must not have incoming connections.")
        if kind == "Output" and len(parents[node_id]) > 1:
            problems.append(f"Node '{node_id}' (Output) only reads its first input.")
        if kind == "Join":
            incoming = len(parents[node_id])
            if incoming == 1:
                problems.append(
                    f"Node '{node_id}' (Join Tables) needs two incoming connections: "
                    "the first one is the left table, the second one is the right table."
                )
            elif incoming > 2:
                problems.append(
                    f"Node '{node_id}' (Join Tables) supports exactly two incoming connections, got {incoming}."
                )

    return problems


__all__ = [
    "AGGREGATIONS",
    "JOIN_TYPES",
    "KIND_PREFIX",
    "NODE_KINDS",
    "NODE_REGISTRY",
    "OUTPUT_TYPES",
    "PIVOT_STYLE",
    "SOURCE_TYPES",
    "TRANSFORM_TYPES",
    "_TRANSFORM_KIND",
    "build_label",
    "build_node",
    "build_node_data",
    "default_values",
    "fields_for",
    "format_aggregations",
    "get_node_class",
    "new_node_id",
    "node_kind",
    "node_values",
    "palette_entry",
    "parse_aggregations",
    "parse_columns",
    "validate_pipeline",
]
