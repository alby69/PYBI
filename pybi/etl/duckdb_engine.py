"""DuckDB Transformation Engine for converting JSON step sequences into DuckDB CTE SQL queries."""

import os
import time
import logging
from typing import Any, Dict, List, Optional, Union

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
            target_steps = raw_steps[:step_index]
        else:
            target_steps = raw_steps

        # Build Source CTE (step_0)
        source_type = (source_info.get("type") or source_info.get("source_type") or "").lower()
        filepath = source_info.get("path") or source_info.get("file_path") or source_info.get("filepath")
        table_name = source_info.get("table") or source_info.get("table_name")

        if source_type in ("postgres", "postgresql"):
            uri = source_info.get("uri") or filepath or ""
            q = source_info.get("query") or table_name or "SELECT *"
            source_sql = f"SELECT * FROM postgres_scan('{uri}', '{q}')"
        elif source_type == "sqlite" and filepath:
            resolved_path = resolve_data_path(filepath, base_dir)
            t_name = table_name or "data"
            source_sql = f"SELECT * FROM sqlite_scan('{resolved_path}', '{t_name}')"
        elif source_type == "parquet" and filepath:
            resolved_path = resolve_data_path(filepath, base_dir)
            source_sql = f"SELECT * FROM read_parquet('{resolved_path}')"
        elif filepath:
            resolved_path = resolve_data_path(filepath, base_dir)
            source_sql = f"SELECT * FROM read_csv_auto('{resolved_path}')"
        elif table_name:
            source_sql = f'SELECT * FROM "{table_name}"'
        else:
            default_path = resolve_data_path("sales_data.csv", base_dir)
            if os.path.exists(default_path):
                source_sql = f"SELECT * FROM read_csv_auto('{default_path}')"
            else:
                source_sql = "SELECT 1 AS placeholder WHERE 1=0"

        ctes: List[str] = [f"step_0 AS (\n  {source_sql}\n)"]

        for idx, step in enumerate(target_steps, start=1):
            prev_cte = f"step_{idx - 1}"
            curr_cte = f"step_{idx}"

            if isinstance(step, dict):
                op = (step.get("operation") or step.get("step_type") or step.get("type") or "").lower().strip()
                params = step.get("params") or step.get("config") or {}
            else:
                op = (getattr(step, "step_type", None) or getattr(step, "operation", "")).lower().strip()
                params = getattr(step, "params", {})

            cte_body = cls._step_to_cte_body(prev_cte, op, params)
            ctes.append(f"{curr_cte} AS (\n  {cte_body}\n)")

        last_cte_name = f"step_{len(target_steps)}"
        sql = "WITH " + ",\n".join(ctes) + f"\nSELECT * FROM {last_cte_name}"
        return sql

    @classmethod
    def _step_to_cte_body(cls, prev_cte: str, op: str, params: Dict[str, Any]) -> str:
        """Helper to translate a single step into SQL for CTE body."""
        if op == "filter":
            cond = params.get("condition") or params.get("predicate")
            if not cond:
                col = params.get("column")
                operator = params.get("operator", "=")
                val = params.get("value")
                if col and val is not None:
                    v_str = f"'{val}'" if isinstance(val, str) else str(val)
                    op_sql = "=" if operator in ("==", "=") else operator
                    cond = f'"{col}" {op_sql} {v_str}'
            if cond:
                return f'SELECT * FROM {prev_cte} WHERE {cond}'
            return f'SELECT * FROM {prev_cte}'

        elif op in ("select", "select_columns", "keep_columns", "remove_other_columns"):
            cols = _as_list(params.get("columns") or params.get("cols") or params.get("keep_columns"))
            if cols:
                cols_str = ", ".join([f'"{c}"' for c in cols])
                return f'SELECT {cols_str} FROM {prev_cte}'
            return f'SELECT * FROM {prev_cte}'

        elif op in ("remove_column", "remove_columns", "drop_column"):
            cols = _as_list(params.get("column") or params.get("columns"))
            if cols:
                cols_str = ", ".join([f'"{c}"' for c in cols])
                return f'SELECT * EXCLUDE ({cols_str}) FROM {prev_cte}'
            return f'SELECT * FROM {prev_cte}'

        elif op in ("rename_column", "rename"):
            mapping = params.get("mapping") or {}
            if not mapping and params.get("old_column") and params.get("new_column"):
                mapping = {params["old_column"]: params["new_column"]}
            if mapping:
                renames = ", ".join([f'"{k}" AS "{v}"' for k, v in mapping.items()])
                return f'SELECT * RENAME ({renames}) FROM {prev_cte}'
            return f'SELECT * FROM {prev_cte}'

        elif op in ("cast_column", "cast", "change_type"):
            casts = params.get("casts") or {}
            if not casts and params.get("column") and params.get("target_type"):
                casts = {params["column"]: params["target_type"]}
            if casts:
                type_map = {
                    "text": "VARCHAR", "string": "VARCHAR", "varchar": "VARCHAR",
                    "int": "BIGINT", "integer": "BIGINT", "bigint": "BIGINT",
                    "float": "DOUBLE", "double": "DOUBLE", "numeric": "DOUBLE",
                    "boolean": "BOOLEAN", "bool": "BOOLEAN",
                    "date": "DATE", "timestamp": "TIMESTAMP", "datetime": "TIMESTAMP",
                }
                replaces = ", ".join([
                    f'CAST("{c}" AS {type_map.get(str(t).lower(), str(t).upper())}) AS "{c}"'
                    for c, t in casts.items()
                ])
                return f'SELECT * REPLACE ({replaces}) FROM {prev_cte}'
            return f'SELECT * FROM {prev_cte}'

        elif op in ("add_column", "calculated_column", "custom_column"):
            new_col = params.get("new_column") or params.get("column") or "custom_col"
            expr = params.get("expression")
            cols = _as_list(params.get("columns"))
            sep = params.get("separator", " ")
            if expr:
                return f'SELECT *, ({expr}) AS "{new_col}" FROM {prev_cte}'
            elif cols:
                cols_str = ", ".join([f'"{c}"' for c in cols])
                return f'SELECT *, CONCAT_WS(\'{sep}\', {cols_str}) AS "{new_col}" FROM {prev_cte}'
            return f'SELECT *, NULL AS "{new_col}" FROM {prev_cte}'

        elif op in ("conditional_column", "conditional"):
            new_col = params.get("new_column") or "conditional_col"
            if_cond = params.get("if_condition") or params.get("condition")
            then_val = params.get("then_value") or params.get("then")
            else_val = params.get("else_value") if params.get("else_value") is not None else params.get("else")
            cases = params.get("cases") or []

            if cases:
                parts = []
                for item in cases:
                    c = item.get("when") or item.get("if_condition")
                    v = item.get("then") or item.get("then_value")
                    v_str = f"'{v}'" if isinstance(v, str) else str(v)
                    parts.append(f"WHEN {c} THEN {v_str}")
                e_str = f"'{else_val}'" if isinstance(else_val, str) else str(else_val)
                case_sql = f"CASE {' '.join(parts)} ELSE {e_str} END"
                return f'SELECT *, ({case_sql}) AS "{new_col}" FROM {prev_cte}'
            elif if_cond:
                t_str = f"'{then_val}'" if isinstance(then_val, str) else str(then_val)
                e_str = f"'{else_val}'" if isinstance(else_val, str) else (str(else_val) if else_val is not None else "NULL")
                case_sql = f"CASE WHEN {if_cond} THEN {t_str} ELSE {e_str} END"
                return f'SELECT *, ({case_sql}) AS "{new_col}" FROM {prev_cte}'
            return f'SELECT * FROM {prev_cte}'

        elif op in ("deduplicate", "distinct", "remove_duplicates"):
            cols = _as_list(params.get("columns"))
            if cols:
                cols_str = ", ".join([f'"{c}"' for c in cols])
                return f'SELECT DISTINCT ON ({cols_str}) * FROM {prev_cte}'
            return f'SELECT DISTINCT * FROM {prev_cte}'

        elif op in ("sort", "sort_rows", "order_by"):
            cols = _as_list(params.get("by") or params.get("column") or params.get("columns"))
            desc = bool(params.get("descending", False))
            if cols:
                cols_str = ", ".join([f'"{c}"' for c in cols])
                order_dir = "DESC" if desc else "ASC"
                return f'SELECT * FROM {prev_cte} ORDER BY {cols_str} {order_dir}'
            return f'SELECT * FROM {prev_cte}'

        elif op in ("group_by", "groupby"):
            group_cols = _as_list(params.get("group_by") or params.get("by") or params.get("columns"))
            aggs = params.get("aggregations", {})
            if group_cols:
                g_str = ", ".join([f'"{c}"' for c in group_cols])
                agg_parts = []
                for c_name, fn in aggs.items():
                    fn_str = str(fn).upper()
                    agg_parts.append(f'{fn_str}("{c_name}") AS "{c_name}_{fn_str.lower()}"')
                agg_str = (", " + ", ".join(agg_parts)) if agg_parts else ""
                return f'SELECT {g_str}{agg_str} FROM {prev_cte} GROUP BY {g_str}'
            return f'SELECT * FROM {prev_cte}'

        elif op in ("replace_values", "replace"):
            col = params.get("column")
            old_val = params.get("old_value")
            new_val = params.get("new_value")
            if col and old_val is not None and new_val is not None:
                o_str = f"'{old_val}'" if isinstance(old_val, str) else str(old_val)
                n_str = f"'{new_val}'" if isinstance(new_val, str) else str(new_val)
                rep = f'CASE WHEN "{col}" = {o_str} THEN {n_str} ELSE "{col}" END AS "{col}"'
                return f'SELECT * REPLACE ({rep}) FROM {prev_cte}'
            return f'SELECT * FROM {prev_cte}'

        elif op in ("text_transform", "format", "text"):
            cols = _as_list(params.get("columns") or params.get("column"))
            act = (params.get("action") or params.get("transform_action") or "trim").lower()
            if cols:
                replaces = []
                for c in cols:
                    if act == "trim":
                        replaces.append(f'TRIM("{c}") AS "{c}"')
                    elif act in ("upper", "uppercase"):
                        replaces.append(f'UPPER("{c}") AS "{c}"')
                    elif act in ("lower", "lowercase"):
                        replaces.append(f'LOWER("{c}") AS "{c}"')
                if replaces:
                    return f'SELECT * REPLACE ({", ".join(replaces)}) FROM {prev_cte}'
            return f'SELECT * FROM {prev_cte}'

        elif op in ("index_column", "index"):
            col_name = params.get("column_name") or "index"
            start_val = int(params.get("start_value", 1))
            inc_val = int(params.get("increment", 1))
            return f'SELECT (row_number() OVER () * {inc_val} + ({start_val} - {inc_val})) AS "{col_name}", * FROM {prev_cte}'

        else:
            return f'SELECT * FROM {prev_cte}'

    @classmethod
    def generate_preview(
        cls,
        project_id: str,
        query: Union[Dict[str, Any], Any],
        step_index: Optional[int] = None,
        limit: int = 1000,
    ) -> pd.DataFrame:
        """Execute linear transformation query up to step_index applying limit (default 1000 rows)."""
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
            return pl_df.head(limit).to_pandas()

        # Attempt DuckDB CTE SQL generation and execution first
        try:
            sql = cls.to_duckdb_sql(query_dict, step_index=step_index, base_dir=data_dir)
            query_sql = f"{sql} LIMIT {limit}"
            conn = default_binder.duckdb_conn or duckdb.connect(database=":memory:")
            df_res = conn.query(query_sql).df()
            return df_res
        except Exception as err:
            logger.warning("DuckDB CTE execution failed (%s), falling back to ETLExecutor: %s", err, err)

        # Fallback execution via ETLExecutor
        executor = ETLExecutor(duckdb_conn=default_binder.duckdb_conn, base_dir=data_dir)
        stop_at = max(0, step_index) if step_index is not None else None
        res = executor.execute_linear_etl(query_dict, stop_at_step_index=stop_at)

        target_key = f"step_{stop_at}" if stop_at is not None and stop_at > 0 else "source"
        if target_key in res.dataframes:
            pl_df = res.dataframes[target_key]
        elif res.dataframes:
            pl_df = list(res.dataframes.values())[-1]
        else:
            pl_df = pl.DataFrame()

        return pl_df.head(limit).to_pandas()

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
