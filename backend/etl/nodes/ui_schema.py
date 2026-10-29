"""UI schema definitions and Vue Flow node builders for ETL DAG editor."""

from typing import Any, Dict, List, Optional, Tuple
from pybi.ui.theme import NODE_COLORS

SOURCE_TYPES = ("csv", "parquet", "sqlite")
TRANSFORM_TYPES = (
    "filter",
    "select",
    "groupby",
    "join",
    "pivot",
    "unpivot",
    "fill_down",
    "rename_column",
    "cast_column",
    "split_column",
    "text_transform",
    "deduplicate",
    "conditional_column",
    "index_column",
    "add_column",
)
OUTPUT_TYPES = ("duckdb", "sqlite")
AGGREGATIONS = ("sum", "mean", "min", "max", "count", "first", "last", "median", "std", "n_unique")
JOIN_TYPES = ("inner", "left", "right", "full", "cross", "semi", "anti")
CALCULATED_MODES = ("concat", "expression")

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
    "AddColumn": {
        "label": "Add Calculated Column",
        "icon": "🧮",
        "style": {"background": NODE_COLORS["AddColumn"]["bg"], "border": f"2px solid {NODE_COLORS['AddColumn']['border']}", "borderRadius": "8px", "padding": "10px"},
        "fields": [
            {
                "key": "new_column",
                "label": "New column name",
                "kind": "text",
                "default": "new_column",
                "help": "Name of the column to add (or replace) in the table, e.g. key_sped.",
            },
            {
                "key": "mode",
                "label": "How to build it",
                "kind": "choice",
                "options": {
                    "concat": "Concatenate text columns (A + separator + B)",
                    "expression": "Custom SQL expression",
                },
                "default": "concat",
                "help": "Use the guided text concatenation, or write any DuckDB SQL expression.",
            },
            {
                "key": "columns",
                "label": "Columns to concatenate (in order)",
                "kind": "columns",
                "default": "",
                "help": "Pick the text columns in the order you want them joined. You can add more by typing a name.",
            },
            {
                "key": "separator",
                "label": "Separator",
                "kind": "text",
                "default": "_",
                "help": "Text placed between the columns, e.g. _ or a space or -.",
            },
            {
                "key": "trim",
                "label": "Trim spaces around values",
                "kind": "bool",
                "default": True,
                "help": "Removes leading/trailing spaces from each value before joining (recommended for join keys).",
            },
            {
                "key": "expression",
                "label": "SQL expression",
                "kind": "text",
                "default": "",
                "help": "Used only in expression mode, e.g. upper(trim(\"Nome\")) || '_' || trim(\"Citta\").",
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
    "Unpivot": "unpivot",
    "FillDown": "fill",
    "RenameColumn": "rename",
    "CastColumn": "cast",
    "SplitColumn": "split",
    "TextTransform": "text",
    "Deduplicate": "dedup",
    "ConditionalColumn": "cond",
    "IndexColumn": "idx",
    "AddColumn": "calc",
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
    "unpivot": "Unpivot",
    "fill_down": "FillDown",
    "filldown": "FillDown",
    "rename_column": "RenameColumn",
    "rename": "RenameColumn",
    "cast_column": "CastColumn",
    "cast": "CastColumn",
    "split_column": "SplitColumn",
    "split": "SplitColumn",
    "text_transform": "TextTransform",
    "text": "TextTransform",
    "deduplicate": "Deduplicate",
    "distinct": "Deduplicate",
    "conditional_column": "ConditionalColumn",
    "conditional": "ConditionalColumn",
    "index_column": "IndexColumn",
    "index": "IndexColumn",
    "add_column": "AddColumn",
    "addcolumn": "AddColumn",
    "calculated_column": "AddColumn",
}


def new_node_id(kind: str, existing_ids: List[str]) -> str:
    """Build a unique node id for a new node of the given kind."""
    prefix = KIND_PREFIX.get(kind, "node")
    taken = set(existing_ids)
    index = 1
    while f"{prefix}_{index}" in taken:
        index += 1
    return f"{prefix}_{index}"


def build_label(kind: str, data: Dict[str, Any]) -> str:
    """Build the human readable node label shown on the canvas."""
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
        aggs = ", ".join(f"{col}:{fn}" for col, fn in data.get("aggregations", {}).items()) if data.get("aggregations") else ""
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
    if kind == "Unpivot":
        on_cols = ", ".join(data.get("on", [])) if isinstance(data.get("on"), list) else str(data.get("on") or "")
        return f"{icon} Unpivot ({on_cols})"
    if kind == "FillDown":
        cols = ", ".join(data.get("columns", [])) if isinstance(data.get("columns"), list) else str(data.get("columns") or "")
        return f"{icon} Fill Down ({cols})"
    if kind == "RenameColumn":
        return f"{icon} Rename Columns"
    if kind == "CastColumn":
        return f"{icon} Change Data Types"
    if kind == "SplitColumn":
        col = data.get("column") or ""
        delim = data.get("delimiter") or " "
        return f"{icon} Split {col} ['{delim}']"
    if kind == "TextTransform":
        act = data.get("transform_action") or "trim"
        cols = ", ".join(data.get("columns", [])) if isinstance(data.get("columns"), list) else str(data.get("columns") or "")
        return f"{icon} {act.capitalize()} ({cols})"
    if kind == "Deduplicate":
        cols = ", ".join(data.get("columns", [])) if isinstance(data.get("columns"), list) else str(data.get("columns") or "")
        return f"{icon} Deduplicate ({cols if cols else 'all'})"
    if kind == "ConditionalColumn":
        new_col = data.get("new_column") or "conditional_col"
        return f"{icon} If-Then ({new_col})"
    if kind == "IndexColumn":
        col_name = data.get("column_name") or "index"
        return f"{icon} Index ({col_name})"
    if kind == "AddColumn":
        new_column = data.get("new_column") or "new_column"
        if (data.get("mode") or "concat") == "expression":
            return f"{icon} Add Column ({new_column} = SQL)"
        columns = data.get("columns") or []
        if isinstance(columns, str):
            columns = [part.strip() for part in columns.split(",") if part.strip()]
        separator = data.get("separator") if data.get("separator") is not None else "_"
        return f"{icon} Add Column ({new_column} = {' + '.join(str(c) for c in columns)} [{separator}])"
    if kind == "Output":
        table_name = data.get("table_name", "")
        if data.get("output_type") == "sqlite":
            return f"{icon} SQLite Table ({data.get('file_path', 'output.db')}) -> {table_name}"
        return f"{icon} DuckDB Table ({table_name})"
    return f"{icon} {template['label']}"


def build_node_data(kind: str, values: Dict[str, Any]) -> Dict[str, Any]:
    """Validate form values and build the executor node data payload."""
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
        columns = [c.strip() for c in columns.split(",") if c.strip()] if isinstance(columns, str) else list(columns or [])
        if not columns:
            raise ValueError("At least one column is required for a Select node.")
        return {"node_type": "Transform", "transform_type": "select", "columns": columns}

    if kind == "GroupBy":
        group_by = values.get("group_by")
        group_by = [c.strip() for c in group_by.split(",") if c.strip()] if isinstance(group_by, str) else list(group_by or [])
        if not group_by:
            raise ValueError("At least one grouping column is required for a Group By node.")
        aggregations = values.get("aggregations")
        if isinstance(aggregations, str):
            res = {}
            for chunk in aggregations.split(","):
                pair = chunk.strip()
                if not pair:
                    continue
                if ":" not in pair:
                    raise ValueError(f"Invalid aggregation '{pair}'. Expected 'column:function', e.g. 'sales:sum'.")
                col, func = (p.strip() for p in pair.split(":", 1))
                if func not in AGGREGATIONS:
                    raise ValueError(f"Unsupported aggregation '{func}'. Supported: {', '.join(AGGREGATIONS)}.")
                res[col] = func
            aggregations = res
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
        left_on = [c.strip() for c in left_on.split(",") if c.strip()] if isinstance(left_on, str) else list(left_on or [])
        right_on = values.get("right_on")
        right_on = [c.strip() for c in right_on.split(",") if c.strip()] if isinstance(right_on, str) else list(right_on or [])
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
        index = [c.strip() for c in index.split(",") if c.strip()] if isinstance(index, str) else list(index or [])
        on = values.get("on")
        on = [c.strip() for c in on.split(",") if c.strip()] if isinstance(on, str) else list(on or [])
        raw_vals = values.get("values")
        val_cols = [c.strip() for c in raw_vals.split(",") if c.strip()] if isinstance(raw_vals, str) else list(raw_vals or [])
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

    if kind == "Unpivot":
        index = values.get("index")
        index = [c.strip() for c in index.split(",") if c.strip()] if isinstance(index, str) else list(index or [])
        on = values.get("on")
        on = [c.strip() for c in on.split(",") if c.strip()] if isinstance(on, str) else list(on or [])
        if not on:
            raise ValueError("At least one column to unpivot is required for an Unpivot node.")
        return {
            "node_type": "Transform",
            "transform_type": "unpivot",
            "index": index,
            "on": on,
            "variable_name": (values.get("variable_name") or "variable").strip(),
            "value_name": (values.get("value_name") or "value").strip(),
        }

    if kind == "FillDown":
        cols = values.get("columns")
        cols = [c.strip() for c in cols.split(",") if c.strip()] if isinstance(cols, str) else list(cols or [])
        if not cols:
            raise ValueError("At least one column to fill is required for a Fill Down node.")
        order_by = (values.get("order_by") or "").strip()
        return {
            "node_type": "Transform",
            "transform_type": "fill_down",
            "columns": cols,
            "order_by": order_by or None,
        }

    if kind == "RenameColumn":
        raw_map = values.get("column_mapping")
        m = {}
        if isinstance(raw_map, dict):
            m = raw_map
        elif isinstance(raw_map, str):
            for chunk in raw_map.split(","):
                if ":" in chunk:
                    old_c, new_c = chunk.split(":", 1)
                    if old_c.strip() and new_c.strip():
                        m[old_c.strip()] = new_c.strip()
        if not m:
            raise ValueError("Rename mapping 'old_name:new_name' is required for a Rename Column node.")
        return {
            "node_type": "Transform",
            "transform_type": "rename_column",
            "mapping": m,
            "column_mapping": raw_map,
        }

    if kind == "CastColumn":
        raw_map = values.get("type_mapping")
        c_dict = {}
        if isinstance(raw_map, dict):
            c_dict = raw_map
        elif isinstance(raw_map, str):
            for chunk in raw_map.split(","):
                if ":" in chunk:
                    c, t = chunk.split(":", 1)
                    if c.strip() and t.strip():
                        c_dict[c.strip()] = t.strip()
        if not c_dict:
            raise ValueError("Type mapping 'column:type' is required for a Change Data Type node.")
        return {
            "node_type": "Transform",
            "transform_type": "cast_column",
            "casts": c_dict,
            "type_mapping": raw_map,
        }

    if kind == "SplitColumn":
        col = (values.get("column") or "").strip()
        if not col:
            raise ValueError("Source column is required for a Split Column node.")
        new_cols = values.get("new_columns")
        new_cols = [c.strip() for c in new_cols.split(",") if c.strip()] if isinstance(new_cols, str) else list(new_cols or [])
        if not new_cols:
            raise ValueError("At least one output column name is required for a Split Column node.")
        return {
            "node_type": "Transform",
            "transform_type": "split_column",
            "column": col,
            "delimiter": values.get("delimiter") if values.get("delimiter") is not None else " ",
            "new_columns": new_cols,
        }

    if kind == "TextTransform":
        cols = values.get("columns")
        cols = [c.strip() for c in cols.split(",") if c.strip()] if isinstance(cols, str) else list(cols or [])
        if not cols:
            raise ValueError("Target columns are required for a Format Text node.")
        act = (values.get("transform_action") or "trim").strip()
        return {
            "node_type": "Transform",
            "transform_type": "text_transform",
            "columns": cols,
            "transform_action": act,
        }

    if kind == "Deduplicate":
        cols = values.get("columns")
        cols = [c.strip() for c in cols.split(",") if c.strip()] if isinstance(cols, str) else list(cols or [])
        return {
            "node_type": "Transform",
            "transform_type": "deduplicate",
            "columns": cols,
        }

    if kind == "ConditionalColumn":
        new_col = (values.get("new_column") or "").strip()
        if not new_col:
            raise ValueError("New column name is required for a Conditional Column node.")
        if_cond = (values.get("if_condition") or "").strip()
        if not if_cond:
            raise ValueError("IF condition is required for a Conditional Column node.")
        return {
            "node_type": "Transform",
            "transform_type": "conditional_column",
            "new_column": new_col,
            "if_condition": if_cond,
            "then_value": values.get("then_value"),
            "else_value": values.get("else_value"),
        }

    if kind == "IndexColumn":
        col_name = (values.get("column_name") or "index").strip()
        if not col_name:
            raise ValueError("Index column name is required for an Index Column node.")
        try:
            start_val = int(values.get("start_value", 1))
            inc_val = int(values.get("increment", 1))
        except ValueError:
            raise ValueError("Start value and increment must be integers.")
        return {
            "node_type": "Transform",
            "transform_type": "index_column",
            "column_name": col_name,
            "start_value": start_val,
            "increment": inc_val,
        }

    if kind == "AddColumn":
        new_column = str(values.get("new_column") or "").strip()
        if not new_column:
            raise ValueError("The name of the new column is required.")
        if '"' in new_column or "\n" in new_column:
            raise ValueError('The column name cannot contain double quotes or line breaks.')
        mode = (values.get("mode") or "concat").lower()
        if mode not in CALCULATED_MODES:
            raise ValueError(f"Unsupported calculated column mode '{mode}'. Supported: {', '.join(CALCULATED_MODES)}.")
        data: Dict[str, Any] = {
            "node_type": "Transform",
            "transform_type": "add_column",
            "new_column": new_column,
            "mode": mode,
        }
        if mode == "expression":
            expression = str(values.get("expression") or "").strip()
            if not expression:
                raise ValueError("A SQL expression is required in expression mode.")
            data["expression"] = expression
            return data

        raw_columns = values.get("columns")
        columns = (
            [c.strip() for c in raw_columns.split(",") if c.strip()]
            if isinstance(raw_columns, str)
            else [str(c).strip() for c in (raw_columns or []) if str(c).strip()]
        )
        separator = values.get("separator")
        trim = values.get("trim", True)
        if isinstance(trim, str):
            trim = trim.strip().lower() not in ("false", "0", "no", "off", "")
        # An empty column list is allowed so the node can be created first and
        # wired to an input later; validate_pipeline reports it before running.
        data["columns"] = columns
        data["separator"] = "_" if separator is None else str(separator)
        data["trim"] = bool(trim)
        return data

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
    """Build a complete Vue Flow node from form values."""
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
    """Infer the node kind of an existing graph node."""
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
    """Extract form values from an existing graph node."""
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
        aggs = data.get("aggregations")
        aggs_str = ", ".join(f"{col}:{fn}" for col, fn in aggs.items()) if isinstance(aggs, dict) else ""
        return {"group_by": group_by, "aggregations": aggs_str}
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
    if kind == "Unpivot":
        index = data.get("index") or []
        on = data.get("on") or []
        if isinstance(index, list):
            index = ", ".join(str(c) for c in index)
        if isinstance(on, list):
            on = ", ".join(str(c) for c in on)
        return {
            "index": index,
            "on": on,
            "variable_name": data.get("variable_name") or "variable",
            "value_name": data.get("value_name") or "value",
        }
    if kind == "FillDown":
        cols = data.get("columns") or []
        if isinstance(cols, list):
            cols = ", ".join(str(c) for c in cols)
        return {
            "columns": cols,
            "order_by": data.get("order_by") or "",
        }
    if kind == "RenameColumn":
        mapping = data.get("mapping") or {}
        map_str = data.get("column_mapping") or ", ".join(f"{k}:{v}" for k, v in mapping.items())
        return {"column_mapping": map_str}
    if kind == "CastColumn":
        casts = data.get("casts") or {}
        casts_str = data.get("type_mapping") or ", ".join(f"{k}:{v}" for k, v in casts.items())
        return {"type_mapping": casts_str}
    if kind == "SplitColumn":
        new_cols = data.get("new_columns") or []
        if isinstance(new_cols, list):
            new_cols = ", ".join(str(c) for c in new_cols)
        return {
            "column": data.get("column") or "",
            "delimiter": data.get("delimiter") if data.get("delimiter") is not None else " ",
            "new_columns": new_cols,
        }
    if kind == "TextTransform":
        cols = data.get("columns") or []
        if isinstance(cols, list):
            cols = ", ".join(str(c) for c in cols)
        return {
            "columns": cols,
            "transform_action": data.get("transform_action") or "trim",
        }
    if kind == "Deduplicate":
        cols = data.get("columns") or []
        if isinstance(cols, list):
            cols = ", ".join(str(c) for c in cols)
        return {"columns": cols}
    if kind == "ConditionalColumn":
        return {
            "new_column": data.get("new_column") or "conditional_col",
            "if_condition": data.get("if_condition") or data.get("condition") or "",
            "then_value": data.get("then_value") or data.get("then") or "",
            "else_value": data.get("else_value") if data.get("else_value") is not None else (data.get("else") or ""),
        }
    if kind == "IndexColumn":
        return {
            "column_name": data.get("column_name") or "index",
            "start_value": str(data.get("start_value", 1)),
            "increment": str(data.get("increment", 1)),
        }
    if kind == "AddColumn":
        columns = data.get("columns") or []
        if isinstance(columns, list):
            columns = ", ".join(str(c) for c in columns)
        mode = (data.get("mode") or "concat").lower()
        if mode not in CALCULATED_MODES:
            mode = "concat"
        return {
            "new_column": data.get("new_column") or data.get("column") or "",
            "mode": mode,
            "columns": columns,
            "separator": data.get("separator") if data.get("separator") is not None else "_",
            "trim": bool(data.get("trim", True)),
            "expression": data.get("expression") or "",
        }
    return {
        "table_name": data.get("table_name") or "",
        "output_type": data.get("output_type") or ("sqlite" if data.get("file_path") else "duckdb"),
        "file_path": data.get("file_path") or "output.db",
    }


def default_values(kind: str) -> Dict[str, Any]:
    """Return the default form values for a node kind."""
    if kind not in NODE_KINDS:
        raise ValueError(f"Unknown node kind '{kind}'.")
    return {field["key"]: field.get("default", "") for field in NODE_KINDS[kind]["fields"]}


def fields_for(kind: str) -> List[Dict[str, Any]]:
    """Return the form field metadata for a node kind."""
    if kind not in NODE_KINDS:
        raise ValueError(f"Unknown node kind '{kind}'.")
    return NODE_KINDS[kind]["fields"]


def palette_entry(kind: str) -> Tuple[str, str]:
    """Return the (icon, label) pair shown in the node palette."""
    template = NODE_KINDS[kind]
    return template["icon"], f"{template['icon']} {template['label']}"
