"""Declarative ETL node templates, builders and parsers for the DAG editor.

This module acts as a facade over UI schema definitions (pybi.etl.nodes.ui_schema)
and node class registries (pybi.etl.nodes.registry).
"""

from typing import Any, Dict, List, Optional, Tuple

from pybi.etl.nodes.registry import NODE_REGISTRY, get_node_class
from pybi.etl.nodes.ui_schema import (
    SOURCE_TYPES,
    TRANSFORM_TYPES,
    OUTPUT_TYPES,
    AGGREGATIONS,
    JOIN_TYPES,
    PIVOT_STYLE,
    NODE_KINDS,
    KIND_PREFIX,
    _TRANSFORM_KIND,
    new_node_id,
    build_label,
    build_node_data,
    build_node,
    node_kind,
    node_values,
    default_values,
    fields_for,
    palette_entry,
)


def parse_aggregations(text: str) -> Dict[str, str]:
    """Parse an aggregation text field into a column/function mapping."""
    result: Dict[str, str] = {}
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


def format_aggregations(aggregations: Optional[Dict[str, str]]) -> str:
    """Render an aggregation mapping back to its text field representation."""
    if not aggregations:
        return ""
    return ", ".join(f"{column}:{func}" for column, func in aggregations.items())


def parse_columns(text: str) -> List[str]:
    """Parse a comma separated column list."""
    return [chunk.strip() for chunk in text.split(",") if chunk.strip()]


def validate_pipeline(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> List[str]:
    """Check a pipeline before execution and return human readable problems."""
    problems: List[str] = []
    if not nodes:
        return ["The pipeline has no nodes."]

    ids = {node.get("id") for node in nodes}
    parents: Dict[str, List[str]] = {node_id: [] for node_id in ids}
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
    "SOURCE_TYPES",
    "TRANSFORM_TYPES",
    "OUTPUT_TYPES",
    "AGGREGATIONS",
    "JOIN_TYPES",
    "PIVOT_STYLE",
    "NODE_KINDS",
    "KIND_PREFIX",
    "_TRANSFORM_KIND",
    "NODE_REGISTRY",
    "get_node_class",
    "parse_aggregations",
    "format_aggregations",
    "parse_columns",
    "new_node_id",
    "build_label",
    "build_node_data",
    "build_node",
    "node_kind",
    "node_values",
    "default_values",
    "fields_for",
    "palette_entry",
    "validate_pipeline",
]
