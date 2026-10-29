"""DuckDB Transformation Engine for converting JSON step sequences into DuckDB CTE SQL queries."""

import os
import time
import logging
from typing import Any, Dict, List, Optional, Set, Union

import duckdb
import pandas as pd
import polars as pl

from pybi.core.storage import default_storage
from pybi.dashboard.binding import default_binder
from pybi.etl.executor import ETLExecutor
from pybi.etl.paths import resolve_data_path
import pybi.storage.project_manager as pm

logger = logging.getLogger(__name__)


def _as_list(val: Any) -> List[str]:
    """Helper to convert string/list into a list of strings."""
    if val is None:
        return []
    if isinstance(val, str):
        return [s.strip() for s in val.split(",") if s.strip()]
    if isinstance(val, (list, tuple)):
        return [str(s).strip() for s in val if str(s).strip()]
    return [str(val).strip()]


def _format_column(col: str) -> str:
    """Escape column name with double quotes for SQL CTEs."""
    col = str(col).strip()
    if col.startswith('"') and col.endswith('"'):
        return col
    return f'"{col}"'


class ETLEngine:
    """DuckDB SQL-based ETL Transformation Engine."""

    @classmethod
    def load_query(cls, project_id: str) -> Optional[Dict[str, Any]]:
        """Fetch saved ETL query or DAG configuration for project_id."""
        try:
            if not default_storage.project_exists(project_id):
                return None
            dag_dict = pm.load_dag(project_id)
            if not dag_dict or (not dag_dict.get("nodes") and not dag_dict.get("steps") and not dag_dict.get("source")):
                return None
            return dag_dict
        except Exception as err:
            logger.error("Failed to load ETL query for project %s: %s", project_id, err)
            return None

    @classmethod
    def save_query(cls, project_id: str, query: Union[Dict[str, Any], Any]) -> bool:
        """Save ETL query or DAG configuration for project_id."""
        try:
            if hasattr(query, "model_dump"):
                query_dict = query.model_dump()
            elif isinstance(query, dict):
                query_dict = query
            else:
                return False

            if not default_storage.project_exists(project_id):
                default_storage.get_project_dir(project_id)

            pm.save_dag(project_id, query_dict)
            return True
        except Exception as err:
            logger.error("Failed to save ETL query for project %s: %s", project_id, err)
            return False

    @classmethod
    def build_step_clause(
        cls,
        source_table: str,
        step: Union[Dict[str, Any], Any],
        base_dir: Optional[str] = None,
        known_cols: Optional[Set[str]] = None,
    ) -> str:
        """Generate SQL clause for a single step operating on source_table."""
        if hasattr(step, "model_dump"):
            step_dict = step.model_dump()
        elif isinstance(step, dict):
            step_dict = step
        else:
            step_dict = {}

        op = (
            getattr(step, "step_type", None)
            or getattr(step, "operation", None)
            or step_dict.get("step_type")
            or step_dict.get("operation")
            or step_dict.get("type")
            or ""
        ).lower().strip()

        params = (
            getattr(step, "params", None)
            or getattr(step, "parameters", None)
            or step_dict.get("params")
            or step_dict.get("parameters")
            or step_dict.get("config")
            or {}
        )

        return cls._step_to_cte_body(source_table, op, params, base_dir=base_dir, known_cols=known_cols)

    @classmethod
    def execute_steps_duckdb(
        cls,
        conn: duckdb.DuckDBPyConnection,
        source_table: str,
        steps: List[Union[Dict[str, Any], Any]],
        step_index: Optional[int] = None,
        limit: int = 1000,
    ) -> pl.DataFrame:
        """Execute sequence of linear ETL steps on DuckDB connection and return Polars DataFrame."""
        if step_index is not None and step_index >= 0:
            target_steps = steps[: step_index]
        else:
            target_steps = steps

        # Inspect initial column names from source table if present
        known_cols: Set[str] = set()
        try:
            tbl_info = conn.table(source_table)
            known_cols = set(tbl_info.columns)
        except Exception:
            pass

        ctes: List[str] = [f'step_0 AS (\n  SELECT * FROM "{source_table}"\n)']

        for idx, step in enumerate(target_steps, start=1):
            prev_cte = f"step_{idx - 1}"
            curr_cte = f"step_{idx}"

            if hasattr(step, "model_dump"):
                step_dict = step.model_dump()
            elif isinstance(step, dict):
                step_dict = step
            else:
                step_dict = {}

            op = (
                getattr(step, "step_type", None)
                or getattr(step, "operation", None)
                or step_dict.get("step_type")
                or step_dict.get("operation")
                or step_dict.get("type")
                or ""
            ).lower().strip()

            params = (
                getattr(step, "params", None)
                or getattr(step, "parameters", None)
                or step_dict.get("params")
                or step_dict.get("parameters")
                or step_dict.get("config")
                or {}
            )

            cte_body = cls._step_to_cte_body(prev_cte, op, params, known_cols=known_cols)
            ctes.append(f"{curr_cte} AS (\n  {cte_body}\n)")

        last_cte_name = f"step_{len(target_steps)}"
        sql = "WITH " + ",\n".join(ctes) + f"\nSELECT * FROM {last_cte_name}"
        if limit and limit > 0:
            sql += f" LIMIT {limit}"

        arrow_table = conn.sql(sql).to_arrow_table()
        return pl.from_arrow(arrow_table)

    @staticmethod
    def build_sql_query(
        query: Union[Dict[str, Any], Any],
        step_index: int = -1,
        base_dir: Optional[str] = None,
    ) -> str:
        """Build a DuckDB SQL CTE query string for step sequence up to step_index."""
        return ETLEngine.to_duckdb_sql(query, step_index=step_index, base_dir=base_dir)

    @classmethod
    def to_duckdb_sql(
        cls,
        query: Union[Dict[str, Any], Any],
        step_index: Optional[int] = None,
        base_dir: Optional[str] = None,
    ) -> str:
        """Convert linear query JSON steps into DuckDB SQL query using CTE clauses."""
        if hasattr(query, "model_dump"):
            query_dict = query.model_dump()
        elif isinstance(query, dict):
            query_dict = query
        else:
            query_dict = {}

        source_info = query_dict.get("source") or {}
        raw_steps = query_dict.get("steps") or []

        # Determine cutoff
        if step_index is not None and step_index >= 0:
            target_steps = raw_steps[: step_index]
        else:
            target_steps = raw_steps

        source_table = (
            query_dict.get("source_table")
            or source_info.get("table")
            or source_info.get("table_name")
        )
        source_type = (
            source_info.get("type") or source_info.get("source_type") or ""
        ).lower()
        filepath = (
            source_info.get("path")
            or source_info.get("file_path")
            or source_info.get("filepath")
        )

        if source_type in ("postgres", "postgresql"):
            uri = source_info.get("uri") or filepath or ""
            q = source_info.get("query") or source_table or "SELECT *"
            source_sql = f"SELECT * FROM postgres_scan('{uri}', '{q}')"
        elif source_type == "sqlite" and filepath:
            resolved_path = resolve_data_path(filepath, base_dir)
            t_name = source_table or "data"
            source_sql = f"SELECT * FROM sqlite_scan('{resolved_path}', '{t_name}')"
        elif source_type == "parquet" and filepath:
            resolved_path = resolve_data_path(filepath, base_dir)
            source_sql = f"SELECT * FROM read_parquet('{resolved_path}')"
        elif filepath:
            resolved_path = resolve_data_path(filepath, base_dir)
            source_sql = f"SELECT * FROM read_csv_auto('{resolved_path}')"
        elif source_table:
            if base_dir and os.path.exists(os.path.join(base_dir, source_table)):
                resolved_path = resolve_data_path(source_table, base_dir)
                source_sql = f"SELECT * FROM read_csv_auto('{resolved_path}')"
            elif os.path.exists(source_table):
                source_sql = f"SELECT * FROM read_csv_auto('{source_table}')"
            else:
                source_sql = f'SELECT * FROM "{source_table}"'
        else:
            default_path = resolve_data_path("sales_data.csv", base_dir)
            if os.path.exists(default_path):
                source_sql = f"SELECT * FROM read_csv_auto('{default_path}')"
            else:
                fallback_table = query_dict.get("query_name", "sales")
                source_sql = f'SELECT * FROM "{fallback_table}"'

        ctes: List[str] = [f"step_0 AS (\n  {source_sql}\n)"]
        known_cols: Set[str] = set()

        for idx, step in enumerate(target_steps, start=1):
            prev_cte = f"step_{idx - 1}"
            curr_cte = f"step_{idx}"

            if hasattr(step, "model_dump"):
                step_dict = step.model_dump()
            elif isinstance(step, dict):
                step_dict = step
            else:
                step_dict = {}

            op = (
                getattr(step, "step_type", None)
                or getattr(step, "operation", None)
                or step_dict.get("step_type")
                or step_dict.get("operation")
                or step_dict.get("type")
                or ""
            ).lower().strip()

            params = (
                getattr(step, "params", None)
                or getattr(step, "parameters", None)
                or step_dict.get("params")
                or step_dict.get("parameters")
                or step_dict.get("config")
                or {}
            )

            cte_body = cls._step_to_cte_body(prev_cte, op, params, base_dir=base_dir, known_cols=known_cols)
            ctes.append(f"{curr_cte} AS (\n  {cte_body}\n)")

        last_cte_name = f"step_{len(target_steps)}"
        sql = "WITH " + ",\n".join(ctes) + f"\nSELECT * FROM {last_cte_name}"
        return sql

    @classmethod
    def _step_to_cte_body(
        cls,
        prev_cte: str,
        op: str,
        params: Dict[str, Any],
        base_dir: Optional[str] = None,
        known_cols: Optional[Set[str]] = None,
    ) -> str:
        """Helper to translate a single step into SQL for CTE body."""
        if op in ("filter", "filter_rows"):
            cond = params.get("condition") or params.get("predicate")
            if not cond:
                col = params.get("column")
                operator = str(params.get("operator", "=")).lower().strip()
                val = params.get("value")
                if col and val is not None:
                    col_fmt = _format_column(col)
                    if operator in ("equals", "==", "="):
                        op_sql = "="
                    elif operator in ("not_equals", "!=", "<>"):
                        op_sql = "!="
                    else:
                        op_sql = operator

                    if isinstance(val, str):
                        s_val = val.strip()
                        if (s_val.startswith("'") and s_val.endswith("'")) or (s_val.startswith('"') and s_val.endswith('"')):
                            v_str = s_val
                        elif s_val.replace(".", "", 1).isdigit() or (s_val.startswith("-") and s_val[1:].replace(".", "", 1).isdigit()):
                            v_str = s_val
                        else:
                            v_str = f"'{s_val}'"
                    else:
                        v_str = str(val)
                    cond = f"{col_fmt} {op_sql} {v_str}"
            if cond:
                return f"SELECT * FROM {prev_cte} WHERE {cond}"
            return f"SELECT * FROM {prev_cte}"

        elif op in ("select", "select_columns", "keep_columns", "remove_other_columns"):
            cols = _as_list(params.get("columns") or params.get("cols") or params.get("keep_columns"))
            if cols:
                if known_cols is not None:
                    known_cols.clear()
                    known_cols.update(cols)
                cols_str = ", ".join([_format_column(c) for c in cols])
                return f"SELECT {cols_str} FROM {prev_cte}"
            return f"SELECT * FROM {prev_cte}"

        elif op in ("remove_column", "remove_columns", "drop_column"):
            cols = _as_list(params.get("column") or params.get("columns"))
            if cols:
                if known_cols is not None:
                    for c in cols:
                        known_cols.discard(c)
                cols_str = ", ".join([_format_column(c) for c in cols])
                return f"SELECT * EXCLUDE ({cols_str}) FROM {prev_cte}"
            return f"SELECT * FROM {prev_cte}"

        elif op in ("rename_column", "rename"):
            mapping = params.get("mapping") or {}
            old_col = params.get("old_name") or params.get("old_column")
            new_col = params.get("new_name") or params.get("new_column")
            if not mapping and old_col and new_col:
                mapping = {old_col: new_col}
            if mapping:
                if known_cols is not None:
                    for k, v in mapping.items():
                        if k in known_cols:
                            known_cols.remove(k)
                            known_cols.add(v)
                renames = ", ".join([f"{_format_column(k)} AS {_format_column(v)}" for k, v in mapping.items()])
                return f"SELECT * RENAME ({renames}) FROM {prev_cte}"
            return f"SELECT * FROM {prev_cte}"

        elif op in ("cast_column", "cast", "change_type"):
            casts = params.get("casts") or {}
            col = params.get("column")
            new_t = params.get("new_type") or params.get("target_type")
            if not casts and col and new_t:
                casts = {col: new_t}
            if casts:
                type_map = {
                    "text": "VARCHAR", "string": "VARCHAR", "varchar": "VARCHAR",
                    "int": "BIGINT", "integer": "BIGINT", "bigint": "BIGINT",
                    "float": "DOUBLE", "double": "DOUBLE", "numeric": "DOUBLE",
                    "boolean": "BOOLEAN", "bool": "BOOLEAN",
                    "date": "DATE", "timestamp": "TIMESTAMP", "datetime": "TIMESTAMP",
                }
                replaces = ", ".join([
                    f'CAST({_format_column(c)} AS {type_map.get(str(t).lower(), str(t).upper())}) AS {_format_column(c)}'
                    for c, t in casts.items()
                ])
                return f"SELECT * REPLACE ({replaces}) FROM {prev_cte}"
            return f"SELECT * FROM {prev_cte}"

        elif op in ("add_column", "calculated_column", "custom_column", "add_custom_column"):
            new_col = params.get("new_column") or params.get("column_name") or params.get("column") or "custom_col"
            expr = params.get("expression")
            cols = _as_list(params.get("columns"))
            sep = params.get("separator", " ")
            formatted_new = _format_column(new_col)

            is_existing = known_cols is not None and new_col in known_cols
            if known_cols is not None:
                known_cols.add(new_col)

            prefix = f"SELECT * EXCLUDE ({formatted_new}), " if is_existing else "SELECT *, "

            if expr:
                return f"{prefix}({expr}) AS {formatted_new} FROM {prev_cte}"
            elif cols:
                cols_str = ", ".join([_format_column(c) for c in cols])
                return f"{prefix}CONCAT_WS('{sep}', {cols_str}) AS {formatted_new} FROM {prev_cte}"
            return f"{prefix}NULL AS {formatted_new} FROM {prev_cte}"

        elif op in ("split_column", "split"):
            col = params.get("column") or params.get("column_name")
            delimiter = params.get("delimiter", " ")
            parts = int(params.get("parts", 2))
            new_cols = _as_list(params.get("new_columns"))
            if col:
                exprs = []
                for idx in range(1, parts + 1):
                    target_name = new_cols[idx - 1] if idx - 1 < len(new_cols) else f"{col}_{idx}"
                    if known_cols is not None:
                        known_cols.add(target_name)
                    exprs.append(f'string_split({_format_column(col)}, \'{delimiter}\')[{idx}] AS {_format_column(target_name)}')
                return f"SELECT *, {', '.join(exprs)} FROM {prev_cte}"
            return f"SELECT * FROM {prev_cte}"

        elif op in ("conditional_column", "conditional"):
            new_col = params.get("new_column") or params.get("column_name") or "conditional_col"
            if_cond = params.get("if_condition") or params.get("condition")
            then_val = params.get("then_value") if params.get("then_value") is not None else (params.get("then") if params.get("then") is not None else params.get("val_true"))
            else_val = params.get("else_value") if params.get("else_value") is not None else (params.get("else") if params.get("else") is not None else params.get("val_false"))
            cases = params.get("cases") or []

            if not if_cond and params.get("cond_col"):
                c_col = params.get("cond_col")
                c_op = params.get("cond_op", "=")
                if c_op in ("==", "equals"):
                    c_op = "="
                c_val = params.get("cond_val") if params.get("cond_val") is not None else params.get("value")
                v_str = f"'{c_val}'" if isinstance(c_val, str) else str(c_val)
                if_cond = f"{_format_column(c_col)} {c_op} {v_str}"

            formatted_new = _format_column(new_col)

            is_existing = known_cols is not None and new_col in known_cols
            if known_cols is not None:
                known_cols.add(new_col)
            prefix = f"SELECT * EXCLUDE ({formatted_new}), " if is_existing else "SELECT *, "

            if cases:
                parts = []
                for item in cases:
                    c = item.get("when") or item.get("if_condition")
                    v = item.get("then") or item.get("then_value")
                    v_str = f"'{v}'" if isinstance(v, str) else str(v)
                    parts.append(f"WHEN {c} THEN {v_str}")
                e_str = f"'{else_val}'" if isinstance(else_val, str) else str(else_val)
                case_sql = f"CASE {' '.join(parts)} ELSE {e_str} END"
                return f"{prefix}({case_sql}) AS {formatted_new} FROM {prev_cte}"
            elif if_cond:
                t_str = f"'{then_val}'" if isinstance(then_val, str) else str(then_val)
                e_str = f"'{else_val}'" if isinstance(else_val, str) else (str(else_val) if else_val is not None else "NULL")
                case_sql = f"CASE WHEN {if_cond} THEN {t_str} ELSE {e_str} END"
                return f"{prefix}({case_sql}) AS {formatted_new} FROM {prev_cte}"
            return f"SELECT * FROM {prev_cte}"

        elif op in ("group_by", "groupby"):
            group_cols = _as_list(
                params.get("group_columns") or params.get("group_by_columns") or params.get("group_by") or params.get("by") or params.get("columns")
            )
            aggs = params.get("aggregations", {})
            if group_cols:
                if known_cols is not None:
                    known_cols.clear()
                    known_cols.update(group_cols)
                g_str = ", ".join([_format_column(c) for c in group_cols])
                agg_parts = []
                if isinstance(aggs, dict):
                    for c_name, fn in aggs.items():
                        fn_str = str(fn).upper()
                        alias = f"{c_name}_{fn_str.lower()}"
                        if known_cols is not None:
                            known_cols.add(alias)
                        agg_parts.append(f'{fn_str}({_format_column(c_name)}) AS {_format_column(alias)}')
                elif isinstance(aggs, list):
                    for item in aggs:
                        if isinstance(item, dict):
                            c = item.get("col") or item.get("column")
                            fn_str = str(item.get("agg") or item.get("function") or "sum").upper()
                            alias = item.get("alias") or f"{c}_{fn_str.lower()}"
                            if alias and known_cols is not None:
                                known_cols.add(alias)
                            if c:
                                agg_parts.append(f'{fn_str}({_format_column(c)}) AS {_format_column(alias)}')
                elif isinstance(aggs, str) and aggs.strip():
                    agg_parts.append(aggs.strip())

                agg_str = (", " + ", ".join(agg_parts)) if agg_parts else ""
                return f"SELECT {g_str}{agg_str} FROM {prev_cte} GROUP BY {g_str}"
            return f"SELECT * FROM {prev_cte}"

        elif op in ("merge", "join"):
            right_table = params.get("target_table") or params.get("right_table") or "right_table"
            right_path = params.get("target_path") or params.get("right_path")
            how = (params.get("how") or params.get("join_type") or "left").upper()
            left_on = params.get("left_on") or params.get("source_column") or params.get("on")
            right_on = params.get("right_on") or params.get("target_column") or params.get("on")

            if right_path:
                resolved_right = resolve_data_path(right_path, base_dir)
                right_source = f"read_csv_auto('{resolved_right}')"
            else:
                right_source = f'"{right_table}"'

            if left_on and right_on:
                return (
                    f"SELECT {prev_cte}.*, right_tbl.* EXCLUDE ({_format_column(right_on)}) "
                    f"FROM {prev_cte} {how} JOIN {right_source} AS right_tbl "
                    f"ON {prev_cte}.{_format_column(left_on)} = right_tbl.{_format_column(right_on)}"
                )
            return f"SELECT * FROM {prev_cte}"

        elif op in ("deduplicate", "distinct", "remove_duplicates"):
            cols = _as_list(params.get("columns"))
            if cols:
                cols_str = ", ".join([_format_column(c) for c in cols])
                return f"SELECT DISTINCT ON ({cols_str}) * FROM {prev_cte}"
            return f"SELECT DISTINCT * FROM {prev_cte}"

        elif op in ("sort", "sort_rows", "order_by"):
            cols = _as_list(params.get("by") or params.get("column") or params.get("columns"))
            desc = bool(params.get("descending", False))
            if cols:
                cols_str = ", ".join([_format_column(c) for c in cols])
                order_dir = "DESC" if desc else "ASC"
                return f"SELECT * FROM {prev_cte} ORDER BY {cols_str} {order_dir}"
            return f"SELECT * FROM {prev_cte}"

        elif op in ("replace_values", "replace"):
            col = params.get("column")
            old_val = params.get("old_value")
            new_val = params.get("new_value")
            if col and old_val is not None and new_val is not None:
                o_str = f"'{old_val}'" if isinstance(old_val, str) else str(old_val)
                n_str = f"'{new_val}'" if isinstance(new_val, str) else str(new_val)
                col_fmt = _format_column(col)
                rep = f"CASE WHEN {col_fmt} = {o_str} THEN {n_str} ELSE {col_fmt} END AS {col_fmt}"
                return f"SELECT * REPLACE ({rep}) FROM {prev_cte}"
            return f"SELECT * FROM {prev_cte}"

        elif op in ("text_transform", "format", "text"):
            cols = _as_list(params.get("columns") or params.get("column"))
            act = (params.get("action") or params.get("transform_action") or "trim").lower()
            if cols:
                replaces = []
                for c in cols:
                    c_fmt = _format_column(c)
                    if act == "trim":
                        replaces.append(f"TRIM({c_fmt}) AS {c_fmt}")
                    elif act in ("upper", "uppercase"):
                        replaces.append(f"UPPER({c_fmt}) AS {c_fmt}")
                    elif act in ("lower", "lowercase"):
                        replaces.append(f"LOWER({c_fmt}) AS {c_fmt}")
                if replaces:
                    return f"SELECT * REPLACE ({', '.join(replaces)}) FROM {prev_cte}"
            return f"SELECT * FROM {prev_cte}"

        elif op in ("index_column", "index"):
            col_name = params.get("column_name") or "index"
            start_val = int(params.get("start_value", 1))
            inc_val = int(params.get("increment", 1))
            col_fmt = _format_column(col_name)
            if known_cols is not None:
                known_cols.add(col_name)
            return f"SELECT (row_number() OVER () * {inc_val} + ({start_val} - {inc_val})) AS {col_fmt}, * FROM {prev_cte}"

        else:
            return f"SELECT * FROM {prev_cte}"

    @classmethod
    def generate_preview(
        cls,
        project_id: str,
        query: Union[Dict[str, Any], Any],
        step_index: Optional[int] = None,
        limit: int = 1000,
    ) -> pl.DataFrame:
        """Execute linear transformation query up to step_index applying limit (default 1000 rows).

        Returns a fast Polars DataFrame via PyArrow execution.
        """
        data_dir = default_storage.get_project_data_dir(project_id) if default_storage.project_exists(project_id) else None

        if hasattr(query, "model_dump"):
            query_dict = query.model_dump()
        elif isinstance(query, dict):
            query_dict = query
        else:
            query_dict = {}

        # If query is a visual DAG (has nodes), use ETLExecutor directly
        if "nodes" in query_dict and query_dict["nodes"]:
            executor = ETLExecutor(duckdb_conn=default_binder.duckdb_conn, base_dir=data_dir)
            res = executor.execute(query_dict)
            if res.dataframes:
                pl_df = list(res.dataframes.values())[-1]
            else:
                pl_df = pl.DataFrame()
            return pl_df.head(limit)

        # Attempt DuckDB CTE SQL generation and Arrow -> Polars conversion
        s_idx = -1 if step_index is None else step_index
        sql = cls.build_sql_query(query_dict, step_index=s_idx, base_dir=data_dir)
        query_sql = f"{sql} LIMIT {limit}"
        conn = default_binder.duckdb_conn
        arrow_table = conn.sql(query_sql).to_arrow_table()
        return pl.from_arrow(arrow_table)

    @classmethod
    def execute_full_pipeline(
        cls,
        project_id: str,
        query: Union[Dict[str, Any], Any],
        target_table: str = "target_table",
    ) -> Dict[str, Any]:
        """Execute full ETL transformation pipeline and save/register target table."""
        data_dir = default_storage.get_project_data_dir(project_id) if default_storage.project_exists(project_id) else None
        executor = ETLExecutor(duckdb_conn=default_binder.duckdb_conn, base_dir=data_dir)

        if hasattr(query, "model_dump"):
            query_dict = query.model_dump()
        elif isinstance(query, dict):
            query_dict = query
        else:
            query_dict = {}

        if "nodes" in query_dict and query_dict["nodes"]:
            result = executor.execute(query_dict)
        else:
            result = executor.execute_linear_etl(query_dict)

        if result.status == "error":
            raise RuntimeError(f"ETL Execution failed: {result.error}")

        if target_table in result.output_tables:
            pl_df = result.output_tables[target_table]
        elif result.output_tables:
            pl_df = list(result.output_tables.values())[-1]
        elif result.dataframes:
            pl_df = list(result.dataframes.values())[-1]
        else:
            pl_df = pl.DataFrame()

        # Register in binder and model engine
        default_binder.register_source(target_table, pl_df)

        return {
            "status": "completed",
            "target_table": target_table,
            "rows": len(pl_df),
            "columns": len(pl_df.columns),
            "logs": result.logs,
            "output_tables": list(result.output_tables.keys()) if result.output_tables else [target_table],
        }
