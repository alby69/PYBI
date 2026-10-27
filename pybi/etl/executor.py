"""ETL Execution Engine for PyBI visual DAGs using Polars and DuckDB."""

from dataclasses import dataclass, field
import graphlib
import logging
import os
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import duckdb
import ibis
import polars as pl

from pybi.core.interfaces import ETLNode
from pybi.etl.compiler import ETLCompiler
from pybi.etl.optimizer import SQLOptimizer
from pybi.model.engine import ModelEngine
from pybi.etl.nodes.output import OutputNode

from pybi.etl.connectors import (
    read_csv,
    read_parquet,
    read_postgres,
    read_sqlite,
)
from pybi.etl.node_factory import JOIN_TYPES
from pybi.etl.calculated import apply_calculated_column
from pybi.etl.paths import resolve_data_path

log = logging.getLogger(__name__)


def _as_key_list(value: Any) -> List[str]:
    """Normalise a join key definition into a list of column names."""
    if value is None:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, (list, tuple)):
        return [str(part).strip() for part in value if str(part).strip()]
    return [str(value).strip()]


def _check_join_keys(node_id: str, df: pl.DataFrame, keys: List[str], side: str) -> None:
    """Fail with a helpful message when a join key is missing from its input."""
    missing = [key for key in keys if key not in df.columns]
    if missing:
        raise ValueError(
            f"Join node '{node_id}': {side} input has no column(s) {', '.join(missing)}. "
            f"Available columns: {', '.join(df.columns) or '(none)'}."
        )


def _quote_identifier(name: str) -> str:
    """Quote a table/column identifier for DuckDB."""
    return '"' + str(name).replace('"', '""') + '"'


def _list_temporary_tables(conn: duckdb.DuckDBPyConnection) -> List[str]:
    """Return the ``_pybi_tmp_*`` tables registered on a DuckDB connection.

    ibis' ``list_tables()`` calls ``fetch_arrow_table()``, which newer DuckDB
    releases renamed to ``to_arrow_table()``. Querying ``information_schema``
    directly keeps the executor working with both old and new versions.
    """
    try:
        rows = conn.query(
            "SELECT DISTINCT table_name FROM information_schema.tables"
        ).fetchall()
    except Exception:
        return []
    return [str(row[0]) for row in rows if str(row[0]).startswith("_pybi_tmp_")]


def configure_duckdb_connection(
    conn: duckdb.DuckDBPyConnection,
    threads: Optional[int] = None,
    max_memory: Optional[str] = None,
) -> duckdb.DuckDBPyConnection:
    """Apply performance pragmas to a DuckDB connection."""
    env_threads = os.environ.get("DUCKDB_THREADS")
    env_memory = os.environ.get("DUCKDB_MAX_MEMORY")

    target_threads = threads or (int(env_threads) if env_threads and env_threads.isdigit() else None)
    target_memory = max_memory or env_memory

    if target_threads:
        conn.execute(f"PRAGMA threads={target_threads}")
    if target_memory:
        conn.execute(f"PRAGMA max_memory='{target_memory}'")
    return conn


@dataclass
class ETLResult:
    """Dataclass holding execution results of an ETL DAG pipeline."""

    status: str
    dataframes: Dict[str, pl.DataFrame] = field(default_factory=dict)
    output_tables: Dict[str, pl.DataFrame] = field(default_factory=dict)
    logs: List[str] = field(default_factory=list)
    error: Optional[str] = None


class ETLExecutor:
    """ETLExecutor orchestrates visual Vue Flow DAGs or ETLNode chains using Ibis, SQLGlot, Polars and DuckDB."""

    def __init__(
        self,
        duckdb_conn: Optional[duckdb.DuckDBPyConnection] = None,
        base_dir: Optional[str] = None,
        threads: Optional[int] = None,
        max_memory: Optional[str] = None,
        model_engine: Optional[ModelEngine] = None,
    ) -> None:
        """Initialize ETLExecutor."""
        self.duckdb_conn = duckdb_conn or duckdb.connect(database=":memory:")
        configure_duckdb_connection(self.duckdb_conn, threads=threads, max_memory=max_memory)
        self.base_dir = base_dir

        self.ibis_con = ibis.duckdb.connect()
        self.compiler = ETLCompiler(backend="duckdb", ibis_con=self.ibis_con)
        self.optimizer = SQLOptimizer(dialect="duckdb")
        self.model_engine = model_engine or ModelEngine(conn=self.duckdb_conn)

    def compile(self, dag: Dict[str, Any]) -> Dict[str, str]:
        """Compile visual DAG dict into folded SQL queries per output table."""
        return self.compiler.compile_to_sql(dag)

    def execute_nodes(
        self,
        dag: Sequence[ETLNode],
        source_path: str | None = None,
        source_df: pl.DataFrame | None = None,
        source_table_name: str = "source_data",
    ) -> Tuple[pl.DataFrame, str, str]:
        """Execute a topological list of ETLNodes using Query Folding (compile -> optimize -> execute)."""
        if source_path:
            source_path = resolve_data_path(source_path, self.base_dir)
            if source_path.endswith(".parquet"):
                self.ibis_con.read_parquet(source_path, table_name=source_table_name)
            else:
                self.ibis_con.read_csv(source_path, table_name=source_table_name)
        elif source_df is not None:
            if hasattr(self.ibis_con, "con") and hasattr(self.ibis_con.con, "register"):
                self.ibis_con.con.register(source_table_name, source_df)
            else:
                self.ibis_con.create_table(source_table_name, source_df.to_arrow(), overwrite=True)
        else:
            raise ValueError("Must provide either source_path or source_df to execute_nodes.")

        source_expr = self.ibis_con.table(source_table_name)

        raw_sql = self.compiler.compile(dag, source_expr)
        optimized_sql = self.optimizer.optimize(raw_sql)

        ibis_conn = getattr(self.ibis_con, "con", None)
        if ibis_conn is not None:
            for table in _list_temporary_tables(ibis_conn):
                df_tmp = ibis_conn.query(f"SELECT * FROM {_quote_identifier(table)}").pl()
                self.duckdb_conn.register(table, df_tmp)

        # ``execute(...).pl()`` no longer works on recent DuckDB releases: the
        # connection returned by ``execute`` lost the Polars conversion helper.
        # ``query(...).pl()`` is available on both old and new versions.
        if ibis_conn is not None:
            try:
                result_df = ibis_conn.query(optimized_sql).pl()
            except Exception:
                result_df = self.duckdb_conn.query(optimized_sql).pl()
        else:
            result_df = self.duckdb_conn.query(optimized_sql).pl()

        return result_df, raw_sql, optimized_sql

    def execute(self, dag: Dict[str, Any]) -> ETLResult:
        """Execute a visual DAG defined by nodes and edges."""
        nodes = dag.get("nodes", [])
        edges = dag.get("edges", [])
        logs: List[str] = []

        if not nodes:
            return ETLResult(status="success", logs=["No nodes found in DAG."])

        node_map: Dict[str, Dict[str, Any]] = {n["id"]: n for n in nodes}
        parents_map: Dict[str, List[str]] = {n_id: [] for n_id in node_map}

        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            if source in node_map and target in node_map:
                parents_map[target].append(source)

        try:
            ts = graphlib.TopologicalSorter(parents_map)
            execution_order = list(ts.static_order())
        except graphlib.CycleError as err:
            return ETLResult(
                status="error",
                logs=logs,
                error=f"DAG execution failed due to cycle error: {err}",
            )

        logs.append(f"Topological execution order: {' -> '.join(execution_order)}")
        node_results: Dict[str, pl.DataFrame] = {}
        output_tables: Dict[str, pl.DataFrame] = {}

        for node_id in execution_order:
            node = node_map[node_id]
            parent_ids = parents_map[node_id]

            try:
                df_res, log_msg, output_table_info = self._execute_node(
                    node, parent_ids, node_results
                )
                node_results[node_id] = df_res
                logs.append(f"[{node_id}] {log_msg}")

                if output_table_info:
                    tbl_name, tbl_df = output_table_info
                    output_tables[tbl_name] = tbl_df
                    self.model_engine.register_dataframe(tbl_name, tbl_df, source_node_id=node_id)

            except Exception as e:
                err_msg = f"Error executing node '{node_id}': {e}"
                logs.append(f"[{node_id}] FAILED: {e}")
                return ETLResult(
                    status="error",
                    dataframes=node_results,
                    output_tables=output_tables,
                    logs=logs,
                    error=err_msg,
                )

        return ETLResult(
            status="success",
            dataframes=node_results,
            output_tables=output_tables,
            logs=logs,
        )

    def _execute_node(
        self,
        node: Dict[str, Any],
        parent_ids: List[str],
        node_results: Dict[str, pl.DataFrame],
    ) -> tuple[pl.DataFrame, str, Optional[tuple[str, pl.DataFrame]]]:
        node_id = node.get("id", "unknown")
        data = node.get("data", {})
        label = node.get("label", data.get("label", ""))
        node_type = (
            data.get("node_type")
            or node.get("node_type")
            or data.get("type")
            or node.get("type")
        )

        category = self.compiler._classify_category(node, node_type)

        # 1. DataSource
        if category in ("DataSource", "source", "input_source"):
            df, log_msg = self._load_data_source(node_id, data, label)
            return df, log_msg, None

        # 2. Transform
        elif category in ("Transform", "transform"):
            if not parent_ids:
                raise ValueError(f"Transform node '{node_id}' requires at least one parent input")
            df, log_msg = self._apply_transform(node_id, data, label, parent_ids, node_results)
            return df, log_msg, None

        # 3. Output
        elif category in ("Output", "output", "sink"):
            if not parent_ids:
                raise ValueError(f"Output node '{node_id}' requires a parent input")
            parent_df = node_results[parent_ids[0]]
            out_node = OutputNode(node_id, data=data)
            log_msg, (tbl_name, tbl_df) = out_node.execute(
                parent_df,
                context={"duckdb_conn": self.duckdb_conn, "base_dir": self.base_dir},
            )
            return parent_df, log_msg, (tbl_name, tbl_df)

        else:
            if parent_ids:
                return node_results[parent_ids[0]], f"Unrecognized node category '{category}', passing through parent data", None
            return pl.DataFrame(), f"Unrecognized node category '{category}' with no parents", None

    def _load_data_source(self, node_id: str, data: Dict[str, Any], label: str) -> Tuple[pl.DataFrame, str]:
        source_type = (data.get("source_type") or "").lower()
        filepath = data.get("file_path") or data.get("path") or data.get("filepath") or data.get("uri")

        if not filepath and label:
            match = re.search(r"\(([^)]+)\)", label)
            if match:
                filepath = match.group(1)

        if not source_type:
            if filepath and ("postgres" in filepath or "postgresql" in filepath):
                source_type = "postgres"
            elif filepath and any(filepath.endswith(ext) for ext in (".sqlite", ".db", ".sqlite3")):
                source_type = "sqlite"
            elif filepath and filepath.endswith(".parquet"):
                source_type = "parquet"
            else:
                source_type = "csv"

        if source_type in ("postgres", "postgresql"):
            uri = data.get("uri") or data.get("connection_string") or filepath
            if not uri:
                raise ValueError(f"No URI provided for PostgreSQL DataSource node '{node_id}'")
            query = data.get("query") or data.get("table_name") or data.get("table") or "SELECT 1"
            df = read_postgres(uri, query)
            return df, f"Loaded {len(df)} rows from POSTGRESQL '{uri}'"

        if not filepath:
            raise ValueError(f"No file path provided for DataSource node '{node_id}'")

        filepath = resolve_data_path(filepath, self.base_dir)

        if source_type == "sqlite":
            query_or_table = data.get("query") or data.get("table_name") or data.get("table")
            df = read_sqlite(filepath, query_or_table=query_or_table)
        elif source_type == "parquet":
            df = read_parquet(filepath)
        else:
            df = read_csv(filepath, separator=data.get("csv_separator") or "auto")

        return df, f"Loaded {len(df)} rows from {source_type.upper()} file '{filepath}'"

    def _apply_transform(
        self,
        node_id: str,
        data: Dict[str, Any],
        label: str,
        parent_ids: List[str],
        node_results: Dict[str, pl.DataFrame],
    ) -> Tuple[pl.DataFrame, str]:
        parent_df = node_results[parent_ids[0]]
        transform_type = data.get("transform_type") or data.get("action")

        # Process applied_steps if provided
        applied_steps = data.get("applied_steps", [])
        if applied_steps:
            curr_df = parent_df
            for step in applied_steps:
                config = step.get("config", {})
                cond = config.get("condition") or step.get("condition")
                if cond:
                    temp_conn = self.duckdb_conn
                    temp_conn.register("source_df", curr_df)
                    try:
                        curr_df = temp_conn.query(f"SELECT * FROM source_df WHERE {cond}").pl()
                    finally:
                        try:
                            temp_conn.unregister("source_df")
                        except Exception:
                            pass
            return curr_df, f"Applied {len(applied_steps)} steps sequentially: {len(curr_df)} rows remaining"

        if not transform_type and label:
            label_lower = label.lower()
            if "filter" in label_lower:
                transform_type = "filter"
            elif "add column" in label_lower or "calculated column" in label_lower:
                transform_type = "add_column"
            elif "select" in label_lower:
                transform_type = "select"
            elif "group" in label_lower:
                transform_type = "groupby"
            elif "join" in label_lower:
                transform_type = "join"
            elif "pivot" in label_lower:
                transform_type = "pivot"
            elif "unpivot" in label_lower:
                transform_type = "unpivot"
            elif "fill" in label_lower:
                transform_type = "fill_down"
            elif "rename" in label_lower:
                transform_type = "rename_column"
            elif "cast" in label_lower:
                transform_type = "cast_column"
            elif "split" in label_lower:
                transform_type = "split_column"
            elif "format" in label_lower or "text" in label_lower:
                transform_type = "text_transform"
            elif "dedup" in label_lower or "distinct" in label_lower or "unique" in label_lower:
                transform_type = "deduplicate"
            elif "cond" in label_lower or "if" in label_lower:
                transform_type = "conditional_column"
            elif "index" in label_lower:
                transform_type = "index_column"

        if not transform_type:
            transform_type = "filter"

        if transform_type == "filter":
            condition = data.get("condition") or data.get("predicate")
            if not condition and label:
                match = re.search(r"\(([^)]+)\)", label)
                if match:
                    condition = match.group(1)

            if condition:
                temp_conn = self.duckdb_conn
                temp_conn.register("source_df", parent_df)
                try:
                    filtered_df = temp_conn.query(f"SELECT * FROM source_df WHERE {condition}").pl()
                finally:
                    try:
                        temp_conn.unregister("source_df")
                    except Exception:
                        pass
                return filtered_df, f"Applied filter ({condition}): {len(filtered_df)} rows remaining"
            return parent_df, "Filter node condition empty, passing through data"

        elif transform_type == "select":
            cols = data.get("columns", [])
            if isinstance(cols, str):
                cols = [c.strip() for c in cols.split(",")]
            if cols:
                return parent_df.select(cols), f"Selected columns: {cols}"
            return parent_df, "Select columns empty, passing through data"

        elif transform_type in ("groupby", "group_by"):
            group_cols = data.get("group_by") or data.get("by") or data.get("columns", [])
            if isinstance(group_cols, str):
                group_cols = [c.strip() for c in group_cols.split(",")]

            aggs = data.get("aggregations", {})
            if group_cols:
                if aggs:
                    agg_exprs = []
                    for col_name, agg_func in aggs.items():
                        if hasattr(pl.col(col_name), agg_func):
                            agg_exprs.append(getattr(pl.col(col_name), agg_func)())
                    grouped_df = parent_df.group_by(group_cols).agg(agg_exprs)
                else:
                    grouped_df = parent_df.group_by(group_cols).first()
                return grouped_df, f"Grouped by {group_cols}"
            return parent_df, "GroupBy columns empty, passing through data"

        elif transform_type == "join":
            if len(parent_ids) < 2:
                raise ValueError(
                    f"Join node '{node_id}' requires two parent inputs: the first connection is the "
                    "left table, the second one is the right table."
                )
            left_df = node_results[parent_ids[0]]
            right_df = node_results[parent_ids[1]]
            how = (data.get("how") or data.get("join_type") or "inner").lower()
            if how == "outer":
                how = "full"
            if how not in JOIN_TYPES:
                raise ValueError(
                    f"Unsupported join type '{how}' on node '{node_id}'. "
                    f"Supported: {', '.join(JOIN_TYPES)}."
                )

            if how == "cross":
                joined_df = left_df.join(right_df, how="cross")
                return joined_df, f"Cross joined the two inputs: {len(joined_df)} rows"

            left_on = _as_key_list(data.get("left_on") or data.get("left_column") or data.get("on"))
            right_on = _as_key_list(data.get("right_on") or data.get("right_column") or data.get("on"))
            if not left_on or not right_on:
                raise ValueError(f"Join node '{node_id}' requires both a left and a right key column.")
            if len(left_on) != len(right_on):
                raise ValueError(
                    f"Join node '{node_id}' needs the same number of keys on both sides, got "
                    f"{len(left_on)} left and {len(right_on)} right."
                )
            _check_join_keys(node_id, left_df, left_on, "left")
            _check_join_keys(node_id, right_df, right_on, "right")

            joined_df = left_df.join(right_df, left_on=left_on, right_on=right_on, how=how)
            keys = ", ".join(left_on)
            return joined_df, f"{how.upper()} joined on {keys}: {len(joined_df)} rows"

        elif transform_type == "pivot":
            index_cols = _as_key_list(data.get("index"))
            on_cols = _as_key_list(data.get("on"))
            raw_values = data.get("values")
            if isinstance(raw_values, list) and raw_values and isinstance(raw_values[0], dict):
                val_cols = [v.get("field") for v in raw_values if isinstance(v, dict) and v.get("field")]
            else:
                val_cols = _as_key_list(raw_values)
            agg_fn = data.get("aggregate_function") or "sum"

            if not on_cols:
                raise ValueError(f"Pivot node '{node_id}' requires at least one pivot-on column in 'on'.")

            pivoted_df = parent_df.pivot(
                on=on_cols,
                index=index_cols if index_cols else None,
                values=val_cols if val_cols else None,
                aggregate_function=agg_fn,
            )
            return pivoted_df, f"Pivoted on {on_cols} with aggregate '{agg_fn}': {len(pivoted_df)} rows"

        elif transform_type == "unpivot":
            index_cols = _as_key_list(data.get("index"))
            on_cols = _as_key_list(data.get("on"))
            var_name = data.get("variable_name") or "variable"
            val_name = data.get("value_name") or "value"
            if not on_cols:
                raise ValueError(f"Unpivot node '{node_id}' requires unpivot columns in 'on'.")
            unpivoted_df = parent_df.unpivot(
                index=index_cols if index_cols else None,
                on=on_cols,
                variable_name=var_name,
                value_name=val_name,
            )
            return unpivoted_df, f"Unpivoted columns {on_cols}: {len(unpivoted_df)} rows"

        elif transform_type in ("fill_down", "filldown"):
            cols = _as_key_list(data.get("columns"))
            order_by = data.get("order_by")
            if not cols:
                raise ValueError(f"Fill Down node '{node_id}' requires target columns.")
            df_to_fill = parent_df
            if order_by and order_by in df_to_fill.columns:
                df_to_fill = df_to_fill.sort(order_by)
            exprs = [pl.col(c).forward_fill() for c in cols]
            filled_df = df_to_fill.with_columns(exprs)
            return filled_df, f"Filled down columns {cols}: {len(filled_df)} rows"

        elif transform_type in ("rename_column", "rename"):
            mapping = data.get("mapping") or {}
            if not mapping and data.get("column_mapping"):
                raw_map = str(data.get("column_mapping"))
                mapping = {}
                for chunk in raw_map.split(","):
                    if ":" in chunk:
                        old_c, new_c = chunk.split(":", 1)
                        if old_c.strip() and new_c.strip():
                            mapping[old_c.strip()] = new_c.strip()
            if not mapping:
                raise ValueError(f"Rename Column node '{node_id}' requires a column mapping.")
            renamed_df = parent_df.rename(mapping)
            return renamed_df, f"Renamed columns {mapping}: {len(renamed_df)} rows"

        elif transform_type in ("cast_column", "cast"):
            casts = data.get("casts") or {}
            if not casts and data.get("type_mapping"):
                raw_map = str(data.get("type_mapping"))
                casts = {}
                for chunk in raw_map.split(","):
                    if ":" in chunk:
                        c, t = chunk.split(":", 1)
                        if c.strip() and t.strip():
                            casts[c.strip()] = t.strip()
            if not casts:
                raise ValueError(f"Cast Column node '{node_id}' requires a type mapping.")

            polars_types = {
                "text": pl.Utf8, "string": pl.Utf8, "varchar": pl.Utf8,
                "int": pl.Int64, "integer": pl.Int64, "bigint": pl.Int64,
                "float": pl.Float64, "double": pl.Float64, "numeric": pl.Float64,
                "boolean": pl.Boolean, "bool": pl.Boolean,
                "date": pl.Date, "timestamp": pl.Datetime, "datetime": pl.Datetime,
            }
            exprs = [
                pl.col(c).cast(polars_types.get(t.lower(), pl.Utf8))
                for c, t in casts.items()
            ]
            casted_df = parent_df.with_columns(exprs)
            return casted_df, f"Casted columns {casts}: {len(casted_df)} rows"

        elif transform_type in ("split_column", "split"):
            col = data.get("column")
            delim = data.get("delimiter") if data.get("delimiter") is not None else " "
            new_cols = _as_key_list(data.get("new_columns"))
            if not col:
                raise ValueError(f"Split Column node '{node_id}' requires a source column.")
            if not new_cols:
                raise ValueError(f"Split Column node '{node_id}' requires new column names.")

            split_df = parent_df.with_columns(pl.col(col).str.split(delim).alias("_split_parts"))
            exprs = [
                pl.col("_split_parts").list.get(i).alias(col_name)
                for i, col_name in enumerate(new_cols)
            ]
            res_df = split_df.with_columns(exprs).drop("_split_parts")
            return res_df, f"Split column '{col}' into {new_cols}: {len(res_df)} rows"

        elif transform_type in ("text_transform", "text"):
            cols = _as_key_list(data.get("columns"))
            act = (data.get("transform_action") or data.get("action") or "trim").lower()
            if not cols:
                raise ValueError(f"Text Transform node '{node_id}' requires target columns.")

            exprs = []
            for c in cols:
                if act == "trim":
                    exprs.append(pl.col(c).str.strip_chars())
                elif act in ("upper", "uppercase"):
                    exprs.append(pl.col(c).str.to_uppercase())
                elif act in ("lower", "lowercase"):
                    exprs.append(pl.col(c).str.to_lowercase())
                elif act == "clean":
                    exprs.append(pl.col(c).str.replace_all(r"[^a-zA-Z0-9 ]", ""))
            transformed_df = parent_df.with_columns(exprs)
            return transformed_df, f"Applied text action '{act}' to columns {cols}: {len(transformed_df)} rows"

        elif transform_type in ("deduplicate", "distinct"):
            cols = _as_key_list(data.get("columns"))
            if cols:
                dedup_df = parent_df.unique(subset=cols)
            else:
                dedup_df = parent_df.unique()
            return dedup_df, f"Deduplicated rows ({cols if cols else 'all columns'}): {len(dedup_df)} rows remaining"

        elif transform_type in ("conditional_column", "conditional"):
            new_col = (data.get("new_column") or "conditional_col").strip()
            if_cond = data.get("if_condition") or data.get("condition")
            then_val = data.get("then_value") or data.get("then")
            else_val = data.get("else_value") if data.get("else_value") is not None else data.get("else")
            cases = data.get("cases") or []

            if not if_cond and not cases:
                raise ValueError(f"Conditional Column node '{node_id}' requires an IF condition or cases.")

            if cases:
                parts = []
                for item in cases:
                    cond = item.get("when") or item.get("if_condition")
                    val = item.get("then") or item.get("then_value")
                    v_str = f"'{val}'" if isinstance(val, str) else str(val)
                    parts.append(f"WHEN {cond} THEN {v_str}")
                e_str = f"'{else_val}'" if isinstance(else_val, str) else str(else_val)
                case_sql = f"CASE {' '.join(parts)} ELSE {e_str} END"
            else:
                t_str = f"'{then_val}'" if isinstance(then_val, str) else str(then_val)
                e_str = f"'{else_val}'" if isinstance(else_val, str) else (str(else_val) if else_val is not None else "NULL")
                case_sql = f"CASE WHEN {if_cond} THEN {t_str} ELSE {e_str} END"

            temp_conn = self.duckdb_conn
            temp_conn.register("source_df", parent_df)
            try:
                cond_df = temp_conn.query(f"SELECT *, {case_sql} AS {new_col} FROM source_df").pl()
            finally:
                try:
                    temp_conn.unregister("source_df")
                except Exception:
                    pass
            return cond_df, f"Added conditional column '{new_col}': {len(cond_df)} rows"

        elif transform_type in ("index_column", "index"):
            col_name = data.get("column_name") or "index"
            start_val = int(data.get("start_value", 1))
            inc_val = int(data.get("increment", 1))

            if inc_val == 1 and start_val == 1:
                idx_df = parent_df.with_row_index(name=col_name, offset=1)
            elif inc_val == 1 and start_val == 0:
                idx_df = parent_df.with_row_index(name=col_name, offset=0)
            else:
                df_idx = parent_df.with_row_index(name="_row_num", offset=0)
                idx_df = df_idx.with_columns(
                    (pl.col("_row_num") * inc_val + start_val).alias(col_name)
                ).drop("_row_num")
            return idx_df, f"Added index column '{col_name}' starting at {start_val}: {len(idx_df)} rows"

        elif transform_type in ("add_column", "addcolumn", "calculated_column"):
            new_column = (data.get("new_column") or data.get("column") or "").strip()
            if not new_column:
                raise ValueError(f"Add Column node '{node_id}' requires a name for the new column.")
            result_df = apply_calculated_column(
                parent_df,
                new_column,
                mode=data.get("mode") or "concat",
                columns=data.get("columns"),
                separator=data.get("separator"),
                expression=data.get("expression"),
                trim=bool(data.get("trim", True)),
            )
            return result_df, f"Added calculated column '{new_column}': {len(result_df)} rows"

        else:
            return parent_df, f"Unknown transform '{transform_type}', passing data through"


def execute_dag(
    dag: Dict[str, Any],
    duckdb_conn: Optional[duckdb.DuckDBPyConnection] = None,
    base_dir: Optional[str] = None,
    threads: Optional[int] = None,
    max_memory: Optional[str] = None,
) -> ETLResult:
    """Convenience function to execute an ETL DAG."""
    executor = ETLExecutor(
        duckdb_conn=duckdb_conn,
        base_dir=base_dir,
        threads=threads,
        max_memory=max_memory,
    )
    return executor.execute(dag)
