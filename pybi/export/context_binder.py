"""Context binder module connecting FilterContext and SemanticModel to export payloads."""

from typing import Any, Dict, List, Optional
import polars as pl

from pybi.dashboard.filter_context import FilterContext, FilterState


def bind_filter_context(export_payload: Dict[str, Any], filter_context: Optional[Any] = None) -> Dict[str, Any]:
    """Apply active FilterContext rules to export payload queries and data extractions.

    Args:
        export_payload: Dictionary containing export input (title, widgets, tables, etc.).
        filter_context: Optional FilterContext instance or dict of filter states.

    Returns:
        Enriched payload with active filters metadata, SQL WHERE clauses, and filtered data.
    """
    payload = dict(export_payload)
    active_filters_summary: List[Dict[str, Any]] = []

    ctx: Optional[FilterContext] = None
    if isinstance(filter_context, FilterContext):
        ctx = filter_context
    elif filter_context and hasattr(filter_context, "filters"):
        ctx = filter_context

    if ctx:
        for key, state in ctx.filters.items():
            if hasattr(state, "table"):
                active_filters_summary.append({
                    "key": key,
                    "table": state.table,
                    "column": state.column,
                    "values": state.values,
                    "operator": getattr(state, "operator", "IN"),
                })
            elif isinstance(state, dict):
                active_filters_summary.append(state)
        where_clause = ctx.to_sql_where()
    elif isinstance(filter_context, dict):
        for k, v in filter_context.items():
            vals = v if isinstance(v, list) else [v]
            active_filters_summary.append({
                "key": k,
                "table": k.split(".")[0] if "." in k else "table",
                "column": k.split(".")[1] if "." in k else k,
                "values": vals,
                "operator": "IN",
            })
        where_clause = ""
    else:
        where_clause = ""

    payload["active_filters"] = active_filters_summary
    payload["where_clause"] = where_clause

    # Apply filter filtering to any raw tabular data passed in payload['tables']
    if "tables" in payload and isinstance(payload["tables"], dict):
        filtered_tables: Dict[str, List[Dict[str, Any]]] = {}
        for table_name, rows in payload["tables"].items():
            if not isinstance(rows, list):
                filtered_tables[table_name] = rows
                continue
            table_filters = [f for f in active_filters_summary if f.get("table") == table_name or f.get("key") == table_name]
            if not table_filters or not rows:
                filtered_tables[table_name] = rows
                continue

            # Filter rows in-memory
            filtered_rows = []
            for row in rows:
                keep = True
                for tf in table_filters:
                    col = tf.get("column")
                    vals = tf.get("values", [])
                    op = tf.get("operator", "IN")
                    if col in row:
                        val = row[col]
                        if op == "IN" and val not in vals:
                            keep = False
                            break
                        elif op == "=" and val not in vals and str(val) != str(vals[0] if vals else ""):
                            keep = False
                            break
                if keep:
                    filtered_rows.append(row)
            filtered_tables[table_name] = filtered_rows
        payload["tables"] = filtered_tables

    return payload
