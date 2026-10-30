"""Persistence and query helpers for the PYBI Report View.

The report layout is stored next to the project's ETL/semantic files in
``<project data dir>/report_layout.json``.  Data helpers use the in-memory
``default_binder`` when a table is already registered, then fall back to the
semantic model and finally to the raw project data files (CSV/Parquet/JSON/
SQLite).  Queries are executed with DuckDB so that the same code path works
for small previews and for tables with hundreds of thousands of rows.
"""

from __future__ import annotations

import io
import json
import os
import re
import zipfile
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple
from xml.sax.saxutils import escape

import duckdb
import polars as pl

from pybi.core.model_sync import get_semantic_model_path
from pybi.core.semantic_model import SemanticModel
from pybi.core.storage import default_storage
from pybi.models.report import ReportLayout, VisualWidget

REPORT_LAYOUT_FILENAME = "report_layout.json"
SUPPORTED_DATA_EXTENSIONS = (".csv", ".parquet", ".json", ".sqlite", ".db")


# ---------------------------------------------------------------------------
# Layout persistence
# ---------------------------------------------------------------------------

def get_report_layout_path(project_id: str) -> str:
    """Return the filesystem path of the report layout JSON for a project."""
    data_dir = default_storage.get_project_data_dir(project_id)
    return os.path.join(data_dir, REPORT_LAYOUT_FILENAME)


def load_report_layout(project_id: str) -> ReportLayout:
    """Load the report layout, creating a default single-page report if absent."""
    path = get_report_layout_path(project_id)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            data["project_id"] = project_id
            return ReportLayout.model_validate(data).ensure_valid_state()
        except Exception:
            pass
    return ReportLayout.create_default(project_id).ensure_valid_state()


def save_report_layout(project_id: str, layout: ReportLayout) -> ReportLayout:
    """Persist a report layout to the project data directory."""
    layout.project_id = project_id
    layout.ensure_valid_state()
    path = get_report_layout_path(project_id)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(layout.model_dump(mode="json"), handle, indent=2)
    return layout


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _dtype_to_data_type(dtype: Any) -> str:
    name = str(dtype).lower()
    if "bool" in name:
        return "boolean"
    if "date" in name or "time" in name:
        return "datetime"
    if any(token in name for token in ("int", "uint")):
        return "integer"
    if any(token in name for token in ("float", "decimal", "double")):
        return "number"
    return "string"


def _normalise_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _rows_from_dataframe(df: pl.DataFrame, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    if limit is not None:
        df = df.head(limit)
    rows = df.to_dicts()
    return [{key: _normalise_value(value) for key, value in row.items()} for row in rows]


def _semantic_model(project_id: str) -> Optional[SemanticModel]:
    path = get_semantic_model_path(project_id)
    if not os.path.exists(path):
        return None
    try:
        return SemanticModel.load_yaml_file(path)
    except Exception:
        return None


def _find_project_data_file(project_id: str, table_name: str) -> Optional[str]:
    data_dir = default_storage.get_project_data_dir(project_id)
    target = (table_name or "").lower()
    candidates = []
    for filename in default_storage.list_project_files(project_id):
        stem, ext = os.path.splitext(filename)
        if ext.lower() not in SUPPORTED_DATA_EXTENSIONS:
            continue
        candidates.append((filename, stem.lower(), ext.lower()))
    for filename, stem, _ext in candidates:
        if stem == target:
            return os.path.join(data_dir, filename)
    for filename, stem, _ext in candidates:
        if target in stem or stem in target:
            return os.path.join(data_dir, filename)
    if len(candidates) == 1:
        return os.path.join(data_dir, candidates[0][0])
    return None


def _read_data_file(path: str, table_name: str = "") -> pl.DataFrame:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        from pybi.etl.connectors import read_csv

        return read_csv(path)
    if ext == ".parquet":
        from pybi.etl.connectors import read_parquet

        return read_parquet(path)
    if ext == ".json":
        try:
            return pl.read_json(path)
        except Exception:
            return pl.read_ndjson(path)
    if ext in (".sqlite", ".db"):
        from pybi.etl.connectors import read_sqlite

        return read_sqlite(path, table_name=table_name or None)
    raise ValueError(f"Unsupported data file extension: {ext}")


def load_table_dataframe(project_id: str, table_name: str) -> pl.DataFrame:
    """Load a project table as a Polars DataFrame.

    Resolution order: default DataBinder source, semantic model physical name,
    then raw project files.
    """
    if not table_name:
        raise KeyError("A table name is required")

    try:
        from pybi.dashboard.binding import default_binder

        if table_name in default_binder.list_sources():
            df = default_binder.get_source_data(table_name)
            if isinstance(df, pl.DataFrame):
                return df
            if hasattr(df, "pl"):
                return df.pl()
    except Exception:
        pass

    physical_name = table_name
    model = _semantic_model(project_id)
    if model:
        table = model.get_table(table_name)
        if table is None:
            for candidate in model.tables:
                if candidate.source_table == table_name:
                    table = candidate
                    break
        if table is not None:
            physical_name = table.source_table or table.name

    file_path = _find_project_data_file(project_id, physical_name) or _find_project_data_file(project_id, table_name)
    if not file_path:
        raise KeyError(f"Table '{table_name}' not found in project '{project_id}'")
    return _read_data_file(file_path, physical_name)


def _column_metadata(name: str, dtype: Any, *, is_key: bool = False) -> Dict[str, Any]:
    return {
        "name": name,
        "data_type": _dtype_to_data_type(dtype),
        "is_key": is_key,
        "is_hidden": False,
        "display_folder": None,
    }


def list_report_tables(project_id: str) -> List[Dict[str, Any]]:
    """Return semantic tables (columns + measures) and any extra project files."""
    tables: List[Dict[str, Any]] = []
    seen = set()

    model = _semantic_model(project_id)
    if model:
        for table in model.tables:
            columns = [
                {
                    "name": col.name,
                    "data_type": col.data_type,
                    "is_key": col.is_key,
                    "is_hidden": col.is_hidden,
                    "display_folder": getattr(col, "display_folder", None),
                    "expression": getattr(col, "expression", None),
                    "is_calculated": getattr(col, "is_calculated", False),
                }
                for col in table.columns
            ]
            measures = [
                {
                    "id": f"meas_{table.name}_{measure.name}".lower(),
                    "name": measure.name,
                    "table_name": table.name,
                    "expression": measure.expression or "",
                    "format_string": measure.format_string,
                    "display_folder": None,
                    "is_hidden": False,
                    "agg_func": measure.agg_func or "SUM",
                    "label": measure.label or measure.name,
                }
                for measure in table.measures
            ]
            tables.append(
                {
                    "name": table.name,
                    "source_table": table.source_table,
                    "is_hidden": False,
                    "display_folder": None,
                    "columns": columns,
                    "measures": measures,
                    "type": "semantic",
                }
            )
            seen.add(table.name.lower())
            seen.add(table.source_table.lower())

    try:
        from pybi.dashboard.binding import default_binder

        binder_sources = default_binder.list_sources()
    except Exception:
        binder_sources = []

    file_tables: List[Tuple[str, str]] = []
    for filename in default_storage.list_project_files(project_id):
        stem, ext = os.path.splitext(filename)
        if ext.lower() in SUPPORTED_DATA_EXTENSIONS and stem.lower() not in seen:
            file_tables.append((stem, os.path.join(default_storage.get_project_data_dir(project_id), filename)))

    for source_name in binder_sources:
        if source_name.lower() in seen:
            continue
        try:
            df = load_table_dataframe(project_id, source_name)
            columns = [_column_metadata(name, dtype) for name, dtype in df.schema.items()]
            tables.append(
                {
                    "name": source_name,
                    "source_table": source_name,
                    "is_hidden": False,
                    "display_folder": None,
                    "columns": columns,
                    "measures": [],
                    "type": "source",
                    "row_count": df.height,
                }
            )
            seen.add(source_name.lower())
        except Exception:
            continue

    for stem, path in file_tables:
        if stem.lower() in seen:
            continue
        try:
            df = _read_data_file(path, stem)
            columns = [_column_metadata(name, dtype) for name, dtype in df.schema.items()]
            tables.append(
                {
                    "name": stem,
                    "source_table": stem,
                    "is_hidden": False,
                    "display_folder": None,
                    "columns": columns,
                    "measures": [],
                    "type": "file",
                    "row_count": df.height,
                }
            )
            seen.add(stem.lower())
        except Exception:
            continue

    return tables


def _search_mask(df: pl.DataFrame, search: str) -> pl.Expr:
    pattern = re.escape(search)
    expressions = [
        pl.col(column).cast(pl.Utf8).str.contains(pattern).fill_null(False)
        for column in df.columns
    ]
    if not expressions:
        return pl.lit(True)
    combined = expressions[0]
    for expr in expressions[1:]:
        combined = combined | expr
    return combined


def query_table_data(
    project_id: str,
    table_name: str,
    *,
    limit: int = 5000,
    offset: int = 0,
    sort_by: Optional[str] = None,
    sort_dir: str = "asc",
    search: Optional[str] = None,
) -> Dict[str, Any]:
    """Paginated, sortable and searchable table preview used by Data View."""
    df = load_table_dataframe(project_id, table_name)
    total_rows = df.height
    if search:
        df = df.filter(_search_mask(df, search))
    if sort_by and sort_by in df.columns:
        df = df.sort(sort_by, descending=(str(sort_dir).lower() == "desc"), nulls_last=True)
    page = df.slice(max(0, offset), max(1, min(int(limit), 100000)))
    columns = [
        {
            "name": name,
            "data_type": _dtype_to_data_type(dtype),
            "is_key": name.lower().endswith("key") or name.lower() == "id",
        }
        for name, dtype in page.schema.items()
    ]
    return {
        "table_name": table_name,
        "columns": columns,
        "rows": _rows_from_dataframe(page),
        "total_rows": total_rows,
        "filtered_rows": df.height,
        "offset": offset,
        "limit": limit,
    }


def query_distinct_values(
    project_id: str,
    table_name: str,
    column_name: str,
    *,
    limit: int = 500,
    search: Optional[str] = None,
) -> List[Any]:
    df = load_table_dataframe(project_id, table_name)
    if column_name not in df.columns:
        raise KeyError(f"Column '{column_name}' not found in table '{table_name}'")
    series = df.get_column(column_name)
    if search:
        series = series.filter(series.cast(pl.Utf8).str.contains(re.escape(search)).fill_null(False))
    values = sorted({_normalise_value(value) for value in series.drop_nulls().to_list()}, key=lambda value: str(value))
    return values[: max(1, min(int(limit), 5000))]


# ---------------------------------------------------------------------------
# Visual data query builder
# ---------------------------------------------------------------------------

_OPERATOR_SQL = {
    "eq": "=",
    "equals": "=",
    "neq": "<>",
    "not_equals": "<>",
    "gt": ">",
    "gte": ">=",
    "lt": "<",
    "lte": "<=",
    "contains": "LIKE",
    "not_contains": "NOT LIKE",
    "starts_with": "LIKE",
    "ends_with": "LIKE",
}


def _quote(identifier: str) -> str:
    return '"' + str(identifier).replace('"', '""') + '"'


def _sql_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def _field_column(field: Any) -> str:
    if isinstance(field, str):
        return field
    if not isinstance(field, dict):
        return ""
    return str(field.get("column") or field.get("name") or "")


def _field_kind(field: Any) -> str:
    if isinstance(field, dict):
        return str(field.get("kind") or "")
    return ""


def _field_aggregation(field: Any) -> str:
    if isinstance(field, dict):
        return str(field.get("aggregation") or field.get("agg") or "SUM").upper()
    return "SUM"


def _field_expression(field: Any) -> str:
    if isinstance(field, dict):
        return str(field.get("expression") or "")
    return ""


def _aggregate_sql(field: Any, alias: str) -> str:
    expression = _field_expression(field)
    if expression:
        return f"{expression} AS {_quote(alias)}"
    column = _field_column(field)
    aggregation = _field_aggregation(field)
    if not column:
        return f"COUNT(*) AS {_quote(alias)}"
    column_sql = _quote(column)
    if aggregation in ("COUNT DISTINCT", "COUNT_DISTINCT", "DISTINCTCOUNT"):
        return f"COUNT(DISTINCT {column_sql}) AS {_quote(alias)}"
    if aggregation in ("COUNT", "COUNTROWS"):
        return f"COUNT({column_sql}) AS {_quote(alias)}"
    if aggregation not in ("SUM", "AVG", "MIN", "MAX"):
        aggregation = "SUM"
    return f"{aggregation}({column_sql}) AS {_quote(alias)}"


def _bucket_fields(buckets: Dict[str, Any], *names: str) -> List[Any]:
    for name in names:
        value = buckets.get(name)
        if not value:
            continue
        if isinstance(value, list):
            return [entry for entry in value if entry]
        return [value]
    return []


def _conditions_sql(column: str, conditions: List[Dict[str, Any]], logic: str = "AND") -> str:
    parts: List[str] = []
    for condition in conditions:
        operator = str(condition.get("operator") or "eq").lower()
        value = condition.get("value")
        sql_op = _OPERATOR_SQL.get(operator, "=")
        if operator in ("contains", "not_contains", "starts_with", "ends_with"):
            raw = str(value or "")
            if operator == "contains":
                literal = f"%{raw}%"
            elif operator == "not_contains":
                literal = f"%{raw}%"
            elif operator == "starts_with":
                literal = f"{raw}%"
            else:
                literal = f"%{raw}"
            parts.append(f"CAST({_quote(column)} AS VARCHAR) {sql_op} {_sql_literal(literal)}")
        elif operator in ("in", "not_in"):
            values = value if isinstance(value, list) else [value]
            joined = ", ".join(_sql_literal(entry) for entry in values)
            parts.append(f"{_quote(column)} {'IN' if operator == 'in' else 'NOT IN'} ({joined})")
        elif operator in ("is_null", "is_not_null"):
            parts.append(f"{_quote(column)} IS {'NULL' if operator == 'is_null' else 'NOT NULL'}")
        elif value is None or value == "":
            continue
        else:
            parts.append(f"{_quote(column)} {sql_op} {_sql_literal(value)}")
    joiner = f" {logic.upper()} " if str(logic).upper() == "OR" else " AND "
    return joiner.join(parts) if parts else ""


def _filters_sql(filters: Iterable[Dict[str, Any]]) -> List[str]:
    clauses: List[str] = []
    for entry in filters or []:
        if not isinstance(entry, dict) or entry.get("disabled") or entry.get("is_active") is False:
            continue
        field = entry.get("field") or entry.get("column")
        column = _field_column(field) or (field if isinstance(field, str) else "")
        if not column:
            continue
        mode = str(entry.get("mode") or entry.get("type") or "basic").lower()
        if mode in ("basic", "base"):
            values = entry.get("values") or entry.get("value")
            if values in (None, "", []):
                continue
            if not isinstance(values, list):
                values = [values]
            joined = ", ".join(_sql_literal(value) for value in values)
            clauses.append(f"{_quote(column)} IN ({joined})")
        elif mode in ("advanced", "avanzato"):
            sql = _conditions_sql(column, entry.get("conditions") or [], entry.get("logic") or "AND")
            if sql:
                clauses.append(f"({sql})")
        elif mode in ("topn", "top_n"):
            # Top N is applied after grouping/ordering inside the main query.
            continue
    return clauses


def _top_n(filters: Iterable[Dict[str, Any]]) -> Optional[Tuple[int, str, str]]:
    for entry in filters or []:
        if not isinstance(entry, dict):
            continue
        mode = str(entry.get("mode") or entry.get("type") or "").lower()
        if mode in ("topn", "top_n"):
            count = int(entry.get("top_n") or entry.get("count") or 5)
            direction = str(entry.get("top_direction") or entry.get("direction") or "top").lower()
            by_field = entry.get("by") or entry.get("field")
            column = _field_column(by_field) or "value"
            return max(1, count), ("ASC" if direction in ("bottom", "last", "asc") else "DESC"), column
    return None


def build_visual_data(
    project_id: str,
    widget: Any,
    *,
    extra_filters: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Execute the aggregation query backing a visual and return rows."""
    if isinstance(widget, VisualWidget):
        widget_data = widget.model_dump()
    elif isinstance(widget, dict):
        widget_data = widget
    else:
        raise ValueError("widget must be a VisualWidget or dict")

    buckets = widget_data.get("data_buckets") or {}
    properties = widget_data.get("properties") or {}
    visual_type = str(widget_data.get("type") or "bar_chart").lower()

    all_fields = _bucket_fields(buckets, "x_axis", "category", "axis", "rows", "values", "columns", "y_axis", "measures", "legend", "series", "tooltip")
    table_name = properties.get("table_name") or properties.get("source_table")
    if not table_name:
        for field in all_fields:
            if isinstance(field, dict) and field.get("table"):
                table_name = field["table"]
                break
    if not table_name:
        raise ValueError("No table is bound to this visual")

    df = load_table_dataframe(project_id, table_name)
    con = duckdb.connect(":memory:")
    try:
        con.register("tbl", df.to_pandas())
        filters = list(widget_data.get("filters") or []) + list(extra_filters or [])
        where_clauses = _filters_sql(filters)

        x_fields = _bucket_fields(buckets, "x_axis", "category", "axis", "rows")
        y_fields = _bucket_fields(buckets, "y_axis", "measures", "values")
        legend_fields = _bucket_fields(buckets, "legend", "series", "columns")

        x_field = x_fields[0] if x_fields else None
        y_field = y_fields[0] if y_fields else None
        legend_field = legend_fields[0] if legend_fields else None
        x_col = _field_column(x_field)
        y_col = _field_column(y_field)
        legend_col = _field_column(legend_field)

        select_parts: List[str] = []
        group_parts: List[str] = []
        order_parts: List[str] = []

        if visual_type in ("table", "matrix", "tableex"):
            table_fields = _bucket_fields(buckets, "values", "columns", "rows")
            if not table_fields:
                table_fields = all_fields
            for field in table_fields[:12]:
                column = _field_column(field)
                if not column:
                    continue
                if _field_kind(field) == "measure" or _field_expression(field):
                    select_parts.append(_aggregate_sql(field, column))
                else:
                    select_parts.append(_quote(column))
                    group_parts.append(_quote(column))
            if not select_parts:
                select_parts = ["*"]
        elif visual_type in ("card", "kpi", "gauge", "multi_row_card"):
            if y_fields:
                for field in y_fields[:6]:
                    select_parts.append(_aggregate_sql(field, _field_column(field)))
            elif x_fields:
                select_parts.append(_aggregate_sql(x_field, x_col))
            else:
                select_parts.append("COUNT(*) AS value")
        elif visual_type in ("slicer", "filter"):
            column = x_col or y_col
            if column:
                select_parts = [f"DISTINCT {_quote(column)} AS {_quote(column)}"]
                order_parts = [f"{_quote(column)} ASC"]
            else:
                select_parts = ["*"]
        else:
            if x_col:
                select_parts.append(f"{_quote(x_col)} AS {_quote('category')}")
                group_parts.append(_quote(x_col))
            if legend_col and legend_col != x_col:
                select_parts.append(f"{_quote(legend_col)} AS {_quote('series')}")
                group_parts.append(_quote(legend_col))
            if y_fields:
                for field in y_fields[:6]:
                    select_parts.append(_aggregate_sql(field, "value" if len(y_fields) == 1 else _field_column(field)))
            else:
                select_parts.append("COUNT(*) AS value")

        if not select_parts:
            select_parts = ["*"]

        sql = f"SELECT {', '.join(select_parts)} FROM tbl"
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
        if group_parts:
            sql += " GROUP BY " + ", ".join(group_parts)

        sort_by = properties.get("sort_by")
        sort_dir = str(properties.get("sort_dir") or properties.get("sort_direction") or "").upper()
        order_clause = ""
        if sort_by:
            sort_column = str(sort_by)
            if sort_column not in ("category", "series", "value") and sort_column not in df.columns:
                sort_column = "value"
            order_clause = f"ORDER BY {_quote(sort_column)} {('DESC' if sort_dir == 'DESC' else 'ASC')}"
        elif order_parts:
            order_clause = "ORDER BY " + ", ".join(order_parts)
        elif visual_type in ("bar_chart", "bar", "column_chart", "pie_chart", "donut_chart", "treemap"):
            order_clause = f"ORDER BY {_quote('value')} DESC" if y_fields else ""

        top_n = _top_n(filters)
        row_limit = 10000
        if top_n:
            count, direction, by_column = top_n
            if by_column not in ("category", "series", "value"):
                by_column = "value"
            order_clause = f"ORDER BY {_quote(by_column)} {direction}"
            row_limit = count
        if order_clause:
            sql += f" {order_clause}"
        sql += f" LIMIT {row_limit}"

        relation = con.execute(sql)
        columns = [item[0] for item in relation.description] if relation.description else []
        rows = relation.fetchall()
        result_rows = [dict(zip(columns, (_normalise_value(value) for value in row))) for row in rows]
        return {
            "columns": columns,
            "rows": result_rows,
            "row_count": len(result_rows),
            "generated_sql": sql,
            "table_name": table_name,
        }
    finally:
        con.close()


# ---------------------------------------------------------------------------
# Export helpers (CSV / minimal XLSX without external dependencies)
# ---------------------------------------------------------------------------

def rows_to_csv(columns: List[str], rows: List[Dict[str, Any]]) -> bytes:
    import csv

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(columns)
    for row in rows:
        writer.writerow(["" if row.get(column) is None else row.get(column) for column in columns])
    return buffer.getvalue().encode("utf-8-sig")


def rows_to_xlsx(columns: List[str], rows: List[Dict[str, Any]], sheet_name: str = "Report") -> bytes:
    """Create a minimal valid XLSX workbook using only the stdlib."""
    safe_sheet = re.sub(r"[^A-Za-z0-9_ -]", "_", sheet_name or "Report")[:31] or "Report"

    def column_letter(index: int) -> str:
        letters = ""
        index += 1
        while index:
            index, remainder = divmod(index - 1, 26)
            letters = chr(65 + remainder) + letters
        return letters

    def cell_xml(ref: str, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, bool):
            return f'<c r="{ref}" t="b"><v>{1 if value else 0}</v></c>'
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return f'<c r="{ref}"><v>{value}</v></c>'
        return f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">{escape(str(value))}</t></is></c>'

    sheet_rows: List[str] = []
    header_cells = "".join(cell_xml(f"{column_letter(idx)}1", column) for idx, column in enumerate(columns))
    sheet_rows.append(f'<row r="1">{header_cells}</row>')
    for row_idx, row in enumerate(rows, start=2):
        cells = "".join(
            cell_xml(f"{column_letter(col_idx)}{row_idx}", row.get(column))
            for col_idx, column in enumerate(columns)
        )
        sheet_rows.append(f'<row r="{row_idx}">{cells}</row>')

    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{''.join(sheet_rows)}</sheetData></worksheet>"
    )
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets><sheet name="{escape(safe_sheet)}" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        "</Types>"
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>"
    )
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        "</Relationships>"
    )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return buffer.getvalue()


__all__ = [
    "REPORT_LAYOUT_FILENAME",
    "build_visual_data",
    "get_report_layout_path",
    "list_report_tables",
    "load_report_layout",
    "load_table_dataframe",
    "query_distinct_values",
    "query_table_data",
    "rows_to_csv",
    "rows_to_xlsx",
    "save_report_layout",
]
