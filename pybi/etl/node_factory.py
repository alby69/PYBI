"""Declarative ETL node templates, builders and parsers for the DAG editor.

This module is the single source of truth for the node dictionary contract
consumed by :mod:`pybi.etl.executor`. It is deliberately free of any UI
dependency so it can be imported and tested standalone.
"""

from typing import Any, Dict, List, Optional, Tuple

from pybi.ui.theme import NODE_COLORS

SOURCE_TYPES = ("csv", "parquet", "sqlite")
TRANSFORM_TYPES = ("filter", "select", "groupby", "join", "pivot")
OUTPUT_TYPES = ("duckdb", "sqlite")
AGGREGATIONS = ("sum", "mean", "min", "max", "count", "first", "last", "median", "std", "n_unique")
JOIN_TYPES = ("inner", "left", "right", "full", "cross", "semi", "anti")

# Fallback node styling if Pivot is not in NODE_COLORS
PIVOT_STYLE = {"background": "#FFF8E1", "border": "2px solid #FFA000", "borderRadius": "8px", "padding": "10px"}

NODE_KINDS: Dict[str, Dict[str, Any]] = {
    "DataSource": {
        "label": "Data Source",
        "icon": NODE_COLORS["DataSource"]["icon"],
        "style": {"background": NODE_COLORS["DataSource"]["bg"], "border": f"2px solid {NODE_COLORS['DataSource']['border']}", "borderRadius": "8px", "padding": "10px"},
        "fields": [
            {
                "key": "source_type",
                "label": "Source type",
                "kind": "choice",
                "options": list(SOURCE_TYPES),
                "default": "csv",
                "help": "csv, parquet or sqlite.",
            },
            {
                "key": "csv_separator",
                "label": "CSV separator",
                "kind": "choice",
                "options": {
                    "auto": "Auto-detect",
                    "comma": "Comma ( , )",
                    "semicolon": "Semicolon ( ; )",
                    "tab": "Tab",
                    "pipe": "Pipe ( | )",
                },
                "default": "auto",
                "help": "Delimiter used by the CSV file. Auto-detect sniffs the first rows.",
            },
            {
                "key": "file_path",
                "label": "Data file",
                "kind": "file",
                "default": "sales_data.csv",
                "help": "Pick a file uploaded in this project's data folder, or type a path (absolute, or relative to the app folder).",
            },
            {
                "key": "query",
                "label": "SQL query or table name",
                "kind": "text",
                "default": "",
                "help": "SQLite only. A SELECT/WITH query, or a table name. Empty reads the first table.",
            },
        ],
    },
    "Filter": {
        "label": "Filter Rows",
        "icon": NODE_COLORS["Filter"]["icon"],
        "style": {"background": NODE_COLORS["Filter"]["bg"], "border": f"2px solid {NODE_COLORS['Filter']['border']}", "borderRadius": "8px", "padding": "10px"},
        "fields": [
            {
                "key": "condition",
                "label": "SQL condition",
                "kind": "text",
                "default": "sales > 300",
                "help": "DuckDB WHERE expression. Use single quotes for strings, e.g. region = 'EU'.",
            }
        ],
    },
    "Select": {
        "label": "Select Columns",
        "icon": NODE_COLORS["Select"]["icon"],
        "style": {"background": NODE_COLORS["Select"]["bg"], "border": f"2px solid {NODE_COLORS['Select']['border']}", "borderRadius": "8px", "padding": "10px"},
        "fields": [
            {
                "key": "columns",
                "label": "Columns",
                "kind": "text",
                "default": "region, sales",
                "help": "Comma separated column names to keep.",
            }
        ],
    },
    "GroupBy": {
        "label": "Group By",
        "icon": NODE_COLORS["GroupBy"]["icon"],
        "style": {"background": NODE_COLORS["GroupBy"]["bg"], "border": f"2px solid {NODE_COLORS['GroupBy']['border']}", "borderRadius": "8px", "padding": "10px"},
        "fields": [
            {
                "key": "group_by",
                "label": "Group by columns",
                "kind": "text",
                "default": "region",
                "help": "Comma separated column names to group on.",
            },
            {
                "key": "aggregations",
                "label": "Aggregations",
                "kind": "text",
                "default": "sales:sum",
                "help": "One or more 'column:function' pairs, e.g. 'sales:sum, quantity:sum'.",
            },
        ],
    },
    "Join": {
        "label": "Join Tables",
        "icon": NODE_COLORS["Join"]["icon"],
        "style": {"background": NODE_COLORS["Join"]["bg"], "border": f"2px solid {NODE_COLORS['Join']['border']}", "borderRadius": "8px", "padding": "10px"},
        "fields": [
            {
                "key": "left_on",
                "label": "Left column",
                "kind": "text",
                "default": "region",
                "help": "Key column of the first (upper) input. Comma separated for a composite key.",
            },
            {
                "key": "right_on",
                "label": "Right column",
                "kind": "text",
                "default": "region",
                "help": "Key column of the second (lower) input. Must match the number of left columns.",
            },
            {
                "key": "how",
                "label": "Join type",
                "kind": "choice",
                "options": list(JOIN_TYPES),
                "default": "inner",
                "help": "inner keeps matches, left keeps all left rows, full keeps everything, cross needs no key.",
            },
        ],
    },
    "Pivot": {
        "label": "Pivot Table",
        "icon": "🔄",
        "style": PIVOT_STYLE,
        "fields": [
            {
                "key": "index",
                "label": "Row index columns",
                "kind": "text",
                "default": "region",
                "help": "Comma separated column names for rows.",
            },
            {
                "key": "on",
                "label": "Pivot-on columns",
                "kind": "text",
                "default": "product",
                "help": "Comma separated column names whose values become column headers.",
            },
            {
                "key": "values",
                "label": "Value columns",
                "kind": "text",
                "default": "sales",
                "help": "Comma separated column names to aggregate.",
            },
            {
                "key": "aggregate_function",
                "label": "Aggregation",
                "kind": "choice",
                "options": list(AGGREGATIONS),
                "default": "sum",
                "help": "Aggregation function to apply to values.",
            },
        ],
    },
    "Output": {
        "label": "Output Table",
        "icon": NODE_COLORS["Output"]["icon"],
        "style": {"background": NODE_COLORS["Output"]["bg"], "border": f"2px solid {NODE_COLORS['Output']['border']}", "borderRadius": "8px", "padding": "10px"},
        "fields": [
            {
                "key": "table_name",
                "label": "Table name",
                "kind": "text",
                "default": "output_table",
                "help": "Name registered in DuckDB and exposed to dashboard widgets.",
            },
            {
                "key": "output_type",
                "label": "Destination",
                "kind": "choice",
                "options": list(OUTPUT_TYPES),
                "default": "duckdb",
                "help": "duckdb keeps the table in memory; sqlite also writes a database file.",
            },
            {
                "key": "file_path",
                "label": "SQLite file path",
                "kind": "text",
                "default": "output.db",
                "help": "Only used when Destination is sqlite.",
            },
        ],
    },
}

KIND_PREFIX = {
    "DataSource": "source",
    "Filter": "filter",
    "Select": "select",
    "GroupBy": "group",
    "Join": "join",
    "Pivot": "pivot",
    "Output": "output",
}

_TRANSFORM_KIND = {
    "filter": "Filter",
    "select": "Select",
    "groupby": "GroupBy",
    "group_by": "GroupBy",
    "join": "Join",
    "inner_join": "Join",
    "pivot": "Pivot",
}


def parse_aggregations(text: str) -> Dict[str, str]:
    """Parse an aggregation text field into a column/function mapping.

    Args:
        text: Comma separated 'column:function' pairs.

    Returns:
        Dict[str, str]: Mapping of column name to Polars aggregation name.

    Raises:
        ValueError: If a pair is malformed or uses an unsupported function.
    """
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
    """Render an aggregation mapping back to its text field representation.

    Args:
        aggregations: Optional mapping of column name to aggregation name.

    Returns:
        str: Comma separated 'column:function' pairs.
    """
    if not aggregations:
        return ""
    return ", ".join(f"{column}:{func}" for column, func in aggregations.items())


def parse_columns(text: str) -> List[str]:
    """Parse a comma separated column list.

    Args:
        text: Comma separated column names.

    Returns:
        List[str]: Cleaned column names.
    """
    return [chunk.strip() for chunk in text.split(",") if chunk.strip()]


def new_node_id(kind: str, existing_ids: List[str]) -> str:
    """Build a unique node id for a new node of the given kind.

    Args:
        kind: Node kind key from NODE_KINDS.
        existing_ids: Ids already present in the graph.

    Returns:
        str: Unique node id such as 'filter_3'.
    """
    prefix = KIND_PREFIX.get(kind, "node")
    taken = set(existing_ids)
    index = 1
    while f"{prefix}_{index}" in taken:
        index += 1
    return f"{prefix}_{index}"


def build_label(kind: str, data: Dict[str, Any]) -> str:
    """Build the human readable node label shown on the canvas.

    Args:
        kind: Node kind key from NODE_KINDS.
        data: Node data payload.

    Returns:
        str: Label including the primary parameters in parentheses.
    """
    template = NODE_KINDS[kind]
    icon = template["icon"]

    if kind == "DataSource":
        source_type = data.get("source_type", "csv")
        separators = {"comma": ",", "semicolon": ";", "tab": "tab", "pipe": "|"}
        sep = separators.get(data.get("csv_separator"))
        suffix = f" [{sep}]" if sep else ""
        return f"{icon} {source_type.upper()} Source ({data.get('file_path', '')}{suffix})"
    if kind == "Filter":
        return f"{icon} Filter Rows ({data.get('condition', '')})"
    if kind == "Select":
        return f"{icon} Select Columns ({', '.join(data.get('columns', []))})"
    if kind == "GroupBy":
        group_by = ", ".join(data.get("group_by", []))
        aggs = format_aggregations(data.get("aggregations"))
        return f"{icon} Group By ({group_by}) {aggs}".rstrip()
    if kind == "Join":
        how = (data.get("how") or "inner").lower()
        if how == "cross":
            return f"{icon} Join Tables (cross)"
        left_on = data.get("left_on")
        right_on = data.get("right_on")
        left_label = ", ".join(left_on) if isinstance(left_on, list) else left_on
        right_label = ", ".join(right_on) if isinstance(right_on, list) else right_on
        return f"{icon} {how.upper()} Join ({left_label} = {right_label})"
    if kind == "Pivot":
        on_cols = ", ".join(data.get("on", [])) if isinstance(data.get("on"), list) else str(data.get("on") or "")
        vals = data.get("values", [])
        if isinstance(vals, list):
            val_cols = ", ".join(v.get("field", str(v)) if isinstance(v, dict) else str(v) for v in vals)
        else:
            val_cols = str(vals)
        return f"{icon} Pivot ({val_cols} on {on_cols})"
    if kind == "Output":
        table_name = data.get("table_name", "")
        if data.get("output_type") == "sqlite":
            return f"{icon} SQLite Table ({data.get('file_path', 'output.db')}) -> {table_name}"
        return f"{icon} DuckDB Table ({table_name})"
    return f"{icon} {template['label']}"


def build_node_data(kind: str, values: Dict[str, Any]) -> Dict[str, Any]:
    """Validate form values and build the executor node data payload.

    Args:
        kind: Node kind key from NODE_KINDS.
        values: Raw form values keyed by field key.

    Returns:
        Dict[str, Any]: Node data payload for pybi.etl.executor.

    Raises:
        ValueError: If required values are missing or invalid.
    """
    if kind == "DataSource":
        source_type = values.get("source_type") or "csv"
        if source_type not in SOURCE_TYPES:
            raise ValueError(f"Unsupported source type '{source_type}'.")
        file_path = (values.get("file_path") or "").strip()
        if not file_path:
            raise ValueError("File path is required for a Data Source node.")
        data: Dict[str, Any] = {
            "node_type": "DataSource",
            "source_type": source_type,
            "file_path": file_path,
        }
        if source_type == "csv":
            data["csv_separator"] = values.get("csv_separator") or "auto"
        query = (values.get("query") or "").strip()
        if source_type == "sqlite" and query:
            data["query"] = query
        return data

    if kind == "Filter":
        condition = (values.get("condition") or "").strip()
        if not condition:
            raise ValueError("SQL condition is required for a Filter node.")
        return {"node_type": "Transform", "transform_type": "filter", "condition": condition}

    if kind == "Select":
        columns = values.get("columns")
        columns = parse_columns(columns) if isinstance(columns, str) else list(columns or [])
        if not columns:
            raise ValueError("At least one column is required for a Select node.")
        return {"node_type": "Transform", "transform_type": "select", "columns": columns}

    if kind == "GroupBy":
        group_by = values.get("group_by")
        group_by = parse_columns(group_by) if isinstance(group_by, str) else list(group_by or [])
        if not group_by:
            raise ValueError("At least one grouping column is required for a Group By node.")
        aggregations = values.get("aggregations")
        if isinstance(aggregations, str):
            aggregations = parse_aggregations(aggregations)
        return {
            "node_type": "Transform",
            "transform_type": "groupby",
            "group_by": group_by,
            "aggregations": aggregations or {},
        }

    if kind == "Join":
        how = (values.get("how") or "inner").lower()
        if how == "outer":
            how = "full"
        if how not in JOIN_TYPES:
            raise ValueError(f"Unsupported join type '{how}'. Supported: {', '.join(JOIN_TYPES)}.")
        if how == "cross":
            return {"node_type": "Transform", "transform_type": "join", "how": "cross"}
        left_on = values.get("left_on")
        left_on = parse_columns(left_on) if isinstance(left_on, str) else list(left_on or [])
        right_on = values.get("right_on")
        right_on = parse_columns(right_on) if isinstance(right_on, str) else list(right_on or [])
        if not left_on:
            raise ValueError("Left column is required for a Join node.")
        if not right_on:
            raise ValueError("Right column is required for a Join node.")
        if len(left_on) != len(right_on):
            raise ValueError(
                f"Join needs the same number of keys on both sides, got {len(left_on)} left "
                f"and {len(right_on)} right."
            )
        return {
            "node_type": "Transform",
            "transform_type": "join",
            "how": how,
            "left_on": left_on,
            "right_on": right_on,
        }

    if kind == "Pivot":
        index = values.get("index")
        index = parse_columns(index) if isinstance(index, str) else list(index or [])
        on = values.get("on")
        on = parse_columns(on) if isinstance(on, str) else list(on or [])
        raw_vals = values.get("values")
        val_cols = parse_columns(raw_vals) if isinstance(raw_vals, str) else list(raw_vals or [])
        agg_fn = values.get("aggregate_function") or "sum"
        if not on:
            raise ValueError("At least one pivot-on column is required for a Pivot node.")
        return {
            "node_type": "Transform",
            "transform_type": "pivot",
            "index": index,
            "on": on,
            "values": val_cols,
            "aggregate_function": agg_fn,
        }

    if kind == "Output":
        table_name = (values.get("table_name") or "").strip()
        if not table_name:
            raise ValueError("Table name is required for an Output node.")
        output_type = values.get("output_type") or "duckdb"
        if output_type not in OUTPUT_TYPES:
            raise ValueError(f"Unsupported destination '{output_type}'.")
        data = {"node_type": "Output", "table_name": table_name, "output_type": output_type}
        if output_type == "sqlite":
            file_path = (values.get("file_path") or "").strip() or "output.db"
            data["file_path"] = file_path
        return data

    raise ValueError(f"Unknown node kind '{kind}'.")


def build_node(kind: str, values: Dict[str, Any], node_id: str, position: Dict[str, int]) -> Dict[str, Any]:
    """Build a complete Vue Flow node from form values.

    Args:
        kind: Node kind key from NODE_KINDS.
        values: Raw form values keyed by field key.
        node_id: Unique node id.
        position: Canvas position as {'x': int, 'y': int}.

    Returns:
        Dict[str, Any]: Vue Flow node ready to be appended to the graph.
    """
    if kind not in NODE_KINDS:
        raise ValueError(f"Unknown node kind '{kind}'.")
    data = build_node_data(kind, values)
    template = NODE_KINDS[kind]
    return {
        "id": node_id,
        "label": build_label(kind, data),
        "position": {"x": int(position.get("x", 0)), "y": int(position.get("y", 0))},
        "style": dict(template["style"]),
        "data": data,
    }


def node_kind(node: Dict[str, Any]) -> str:
    """Infer the node kind of an existing graph node.

    Args:
        node: Vue Flow node dictionary.

    Returns:
        str: Node kind key from NODE_KINDS, defaulting to 'DataSource' when unknown.
    """
    data = node.get("data", {}) or {}
    node_type = data.get("node_type")

    if node_type == "Output":
        return "Output"
    if node_type == "DataSource":
        return "DataSource"
    if node_type == "Transform":
        transform_type = (data.get("transform_type") or data.get("action") or "filter").lower()
        return _TRANSFORM_KIND.get(transform_type, "Filter")
    return "DataSource"


def node_values(node: Dict[str, Any]) -> Dict[str, Any]:
    """Extract form values from an existing graph node.

    Args:
        node: Vue Flow node dictionary.

    Returns:
        Dict[str, Any]: Values keyed by NODE_KINDS field keys.
    """
    kind = node_kind(node)
    data = (node.get("data") or {}).copy()

    if kind == "DataSource":
        return {
            "source_type": data.get("source_type") or "csv",
            "file_path": data.get("file_path") or data.get("path") or "",
            "csv_separator": data.get("csv_separator") or "auto",
            "query": data.get("query") or data.get("table_name") or data.get("table") or "",
        }
    if kind == "Filter":
        return {"condition": data.get("condition") or data.get("predicate") or ""}
    if kind == "Select":
        columns = data.get("columns") or []
        if isinstance(columns, list):
            columns = ", ".join(str(c) for c in columns)
        return {"columns": columns}
    if kind == "GroupBy":
        group_by = data.get("group_by") or data.get("by") or []
        if isinstance(group_by, list):
            group_by = ", ".join(str(c) for c in group_by)
        return {"group_by": group_by, "aggregations": format_aggregations(data.get("aggregations"))}
    if kind == "Join":
        left_on = data.get("left_on") or data.get("left_column") or []
        right_on = data.get("right_on") or data.get("right_column") or []
        if isinstance(left_on, list):
            left_on = ", ".join(str(c) for c in left_on)
        if isinstance(right_on, list):
            right_on = ", ".join(str(c) for c in right_on)
        how = (data.get("how") or "inner").lower()
        return {"left_on": left_on, "right_on": right_on, "how": "inner" if how == "cross" else how}
    if kind == "Pivot":
        index = data.get("index") or []
        on = data.get("on") or []
        values = data.get("values") or []
        if isinstance(index, list):
            index = ", ".join(str(c) for c in index)
        if isinstance(on, list):
            on = ", ".join(str(c) for c in on)
        if isinstance(values, list):
            values = ", ".join(str(c) for c in values)
        return {
            "index": index,
            "on": on,
            "values": values,
            "aggregate_function": data.get("aggregate_function") or "sum",
        }
    return {
        "table_name": data.get("table_name") or "",
        "output_type": data.get("output_type") or ("sqlite" if data.get("file_path") else "duckdb"),
        "file_path": data.get("file_path") or "output.db",
    }


def default_values(kind: str) -> Dict[str, Any]:
    """Return the default form values for a node kind.

    Args:
        kind: Node kind key from NODE_KINDS.

    Returns:
        Dict[str, Any]: Default values keyed by field key.
    """
    if kind not in NODE_KINDS:
        raise ValueError(f"Unknown node kind '{kind}'.")
    return {field["key"]: field.get("default", "") for field in NODE_KINDS[kind]["fields"]}


def fields_for(kind: str) -> List[Dict[str, Any]]:
    """Return the form field metadata for a node kind.

    Args:
        kind: Node kind key from NODE_KINDS.

    Returns:
        List[Dict[str, Any]]: Field definitions used to build the editor form.
    """
    if kind not in NODE_KINDS:
        raise ValueError(f"Unknown node kind '{kind}'.")
    return NODE_KINDS[kind]["fields"]


def palette_entry(kind: str) -> Tuple[str, str]:
    """Return the (icon, label) pair shown in the node palette.

    Args:
        kind: Node kind key from NODE_KINDS.

    Returns:
        Tuple[str, str]: Icon emoji and palette label.
    """
    template = NODE_KINDS[kind]
    return template["icon"], f"{template['icon']} {template['label']}"


def validate_pipeline(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> List[str]:
    """Check a pipeline before execution and return human readable problems.

    Args:
        nodes: Graph nodes.
        edges: Graph edges.

    Returns:
        List[str]: Empty list when the pipeline looks executable.
    """
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
