"""ETL Execution Engine for PyBI visual DAGs using Polars and DuckDB."""

from dataclasses import dataclass, field
import graphlib
import os
import re
from typing import Any, Dict, List, Optional, Union

import duckdb
import polars as pl

from .connectors import (
    read_csv,
    read_parquet,
    read_postgres,
    read_sqlite,
    write_postgres,
    write_sqlite,
)
from .node_factory import JOIN_TYPES


def resolve_data_path(filepath: str, base_dir: Optional[str] = None) -> str:
    """Resolve a data file path against the project data folder.

    Resolution order:

    1. An existing absolute path, as given.
    2. ``base_dir/<filepath>``, then ``base_dir/<basename>`` when either exists,
       so a bare file name picked from the project data folder always resolves.
    3. The path as given (absolute, or relative to the process working directory).

    Returns the original path when nothing matches, so error messages keep the
    value the user typed.

    Args:
        filepath: Path or file name from the DataSource node.
        base_dir: Project data directory (see ``FileProjectStorage.get_project_data_dir``).

    Returns:
        The resolved path to read from.
    """
    if not filepath or not base_dir:
        return filepath
    if os.path.isabs(filepath) and os.path.exists(filepath):
        return filepath
    candidates = []
    if not os.path.isabs(filepath):
        candidates.append(os.path.join(base_dir, filepath))
    candidates.append(os.path.join(base_dir, os.path.basename(filepath)))
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return filepath


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


def configure_duckdb_connection(
    conn: duckdb.DuckDBPyConnection,
    threads: Optional[int] = None,
    max_memory: Optional[str] = None,
) -> duckdb.DuckDBPyConnection:
    """Apply performance pragmas to a DuckDB connection.

    Checks explicit parameters or `DUCKDB_THREADS` and `DUCKDB_MAX_MEMORY` environment variables.
    """
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
    """ETLExecutor parses a visual Vue Flow DAG (nodes & edges) and executes it using Polars and DuckDB."""

    def __init__(
        self,
        duckdb_conn: Optional[duckdb.DuckDBPyConnection] = None,
        base_dir: Optional[str] = None,
        threads: Optional[int] = None,
        max_memory: Optional[str] = None,
    ) -> None:
        """Initialize ETLExecutor.

        Args:
            duckdb_conn: Optional DuckDB connection instance.
            base_dir: Project data directory used to resolve DataSource file paths.
            threads: Optional number of threads for DuckDB.
            max_memory: Optional memory limit for DuckDB (e.g., '4GB').
        """
        self.duckdb_conn = duckdb_conn or duckdb.connect(database=":memory:")
        configure_duckdb_connection(self.duckdb_conn, threads=threads, max_memory=max_memory)
        self.base_dir = base_dir

    def execute(self, dag: Dict[str, Any]) -> ETLResult:
        """Execute a DAG defined by nodes and edges.

        Args:
            dag: Dict containing 'nodes' (list) and 'edges' (list).

        Returns:
            ETLResult containing execution status, output DataFrames, and logs.
        """
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

        # Topological sort
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
        """Execute an individual node in the DAG.

        Args:
            node: The node dictionary definition.
            parent_ids: List of parent node IDs.
            node_results: Dict mapping completed node IDs to DataFrames.

        Returns:
            Tuple of (Result DataFrame, Log message, Optional (table_name, DataFrame)).
        """
        node_id = node.get("id", "unknown")
        data = node.get("data", {})
        label = node.get("label", data.get("label", ""))
        node_type = (
            data.get("node_type")
            or node.get("node_type")
            or data.get("type")
            or node.get("type")
        )

        # Classify node type if not explicit
        if not node_type or node_type in ("input", "default", "output"):
            if node_type == "input" or any(k in label for k in ("Source", "CSV", "Parquet", "PostgreSQL", "read_")):
                category = "DataSource"
            elif node_type == "output" or any(k in label for k in ("Output", "Table", "Save")):
                category = "Output"
            else:
                category = "Transform"
        else:
            category = node_type

        # 1. DataSource
        if category in ("DataSource", "source", "input_source"):
            source_type = (data.get("source_type") or "").lower()
            filepath = data.get("file_path") or data.get("path") or data.get("filepath") or data.get("uri")

            # Fallback parsing from label if parameters not explicitly set in data dict
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
                return df, f"Loaded {len(df)} rows from POSTGRESQL '{uri}'", None

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

            return df, f"Loaded {len(df)} rows from {source_type.upper()} file '{filepath}'", None

        # 2. Transform
        elif category in ("Transform", "transform"):
            if not parent_ids:
                raise ValueError(f"Transform node '{node_id}' requires at least one parent input")

            parent_df = node_results[parent_ids[0]]
            transform_type = data.get("transform_type") or data.get("action")

            # Infer transform type from label if absent
            if not transform_type and label:
                label_lower = label.lower()
                if "filter" in label_lower:
                    transform_type = "filter"
                elif "select" in label_lower:
                    transform_type = "select"
                elif "group" in label_lower:
                    transform_type = "groupby"
                elif "join" in label_lower:
                    transform_type = "join"
                elif "pivot" in label_lower:
                    transform_type = "pivot"

            if not transform_type:
                transform_type = "filter"  # default transform fallback

            if transform_type == "filter":
                condition = data.get("condition") or data.get("predicate")
                if not condition and label:
                    match = re.search(r"\(([^)]+)\)", label)
                    if match:
                        condition = match.group(1)

                if condition:
                    # DuckDB SQL evaluation for flexible filter condition support
                    temp_conn = self.duckdb_conn
                    temp_conn.register("source_df", parent_df)
                    try:
                        filtered_df = temp_conn.query(f"SELECT * FROM source_df WHERE {condition}").pl()
                    finally:
                        try:
                            temp_conn.unregister("source_df")
                        except Exception:
                            pass
                    return filtered_df, f"Applied filter ({condition}): {len(filtered_df)} rows remaining", None
                else:
                    return parent_df, "Filter node condition empty, passing through data", None

            elif transform_type == "select":
                cols = data.get("columns", [])
                if isinstance(cols, str):
                    cols = [c.strip() for c in cols.split(",")]
                if cols:
                    selected_df = parent_df.select(cols)
                    return selected_df, f"Selected columns: {cols}", None
                return parent_df, "Select columns empty, passing through data", None

            elif transform_type in ("groupby", "group_by"):
                group_cols = data.get("group_by") or data.get("by") or data.get("columns", [])
                if isinstance(group_cols, str):
                    group_cols = [c.strip() for c in group_cols.split(",")]

                aggs = data.get("aggregations", {})  # e.g. {"sales": "sum"}
                if group_cols:
                    if aggs:
                        agg_exprs = []
                        for col_name, agg_func in aggs.items():
                            if hasattr(pl.col(col_name), agg_func):
                                agg_exprs.append(getattr(pl.col(col_name), agg_func)())
                        grouped_df = parent_df.group_by(group_cols).agg(agg_exprs)
                    else:
                        grouped_df = parent_df.group_by(group_cols).first()
                    return grouped_df, f"Grouped by {group_cols}", None
                return parent_df, "GroupBy columns empty, passing through data", None

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
                    return joined_df, f"Cross joined the two inputs: {len(joined_df)} rows", None

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
                return joined_df, f"{how.upper()} joined on {keys}: {len(joined_df)} rows", None

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
                return pivoted_df, f"Pivoted on {on_cols} with aggregate '{agg_fn}': {len(pivoted_df)} rows", None

            else:
                return parent_df, f"Unknown transform '{transform_type}', passing data through", None

        # 3. Output
        elif category in ("Output", "output", "sink"):
            if not parent_ids:
                raise ValueError(f"Output node '{node_id}' requires a parent input")

            parent_df = node_results[parent_ids[0]]
            table_name = data.get("table_name")

            if not table_name and label:
                match = re.search(r"\(([^)]+)\)", label)
                if match:
                    table_name = match.group(1)

            if not table_name:
                table_name = f"output_{node_id}"

            output_type = (data.get("output_type") or data.get("destination_type") or "").lower()
            filepath = data.get("file_path") or data.get("path") or data.get("filepath") or data.get("uri")

            if output_type in ("postgres", "postgresql") or (filepath and "postgres" in filepath):
                uri = data.get("uri") or data.get("connection_string") or filepath
                if not uri:
                    raise ValueError(f"No URI provided for PostgreSQL Output node '{node_id}'")
                write_postgres(parent_df, uri, table_name)
                log_msg = f"Saved {len(parent_df)} rows to PostgreSQL table '{table_name}'"
            elif output_type == "sqlite" or (filepath and any(filepath.endswith(ext) for ext in (".sqlite", ".db", ".sqlite3"))):
                if not filepath:
                    filepath = "output.db"
                write_sqlite(parent_df, filepath, table_name)
                log_msg = f"Saved {len(parent_df)} rows to SQLite table '{table_name}' at '{filepath}'"
            else:
                log_msg = f"Saved {len(parent_df)} rows to DuckDB table '{table_name}'"

            # Register with DuckDB
            self.duckdb_conn.register(table_name, parent_df)
            return parent_df, log_msg, (table_name, parent_df)

        else:
            # Fallback pass-through
            if parent_ids:
                return node_results[parent_ids[0]], f"Unrecognized node category '{category}', passing through parent data", None
            else:
                return pl.DataFrame(), f"Unrecognized node category '{category}' with no parents", None


def execute_dag(
    dag: Dict[str, Any],
    duckdb_conn: Optional[duckdb.DuckDBPyConnection] = None,
    base_dir: Optional[str] = None,
    threads: Optional[int] = None,
    max_memory: Optional[str] = None,
) -> ETLResult:
    """Convenience function to execute an ETL DAG.

    Args:
        dag: Dict representing the DAG (nodes and edges).
        duckdb_conn: Optional DuckDB connection.
        base_dir: Project data directory used to resolve DataSource file paths.
        threads: Optional number of DuckDB threads.
        max_memory: Optional max memory setting for DuckDB.

    Returns:
        ETLResult instance.
    """
    executor = ETLExecutor(
        duckdb_conn=duckdb_conn,
        base_dir=base_dir,
        threads=threads,
        max_memory=max_memory,
    )
    return executor.execute(dag)
