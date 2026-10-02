"""ETL Execution Engine for PyBI visual DAGs using Polars and DuckDB."""

from dataclasses import dataclass, field
import graphlib
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

    def __init__(self, duckdb_conn: Optional[duckdb.DuckDBPyConnection] = None) -> None:
        """Initialize ETLExecutor.

        Args:
            duckdb_conn: Optional DuckDB connection instance.
        """
        self.duckdb_conn = duckdb_conn or duckdb.connect(database=":memory:")

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

            if source_type == "sqlite":
                query_or_table = data.get("query") or data.get("table_name") or data.get("table")
                df = read_sqlite(filepath, query_or_table=query_or_table)
            elif source_type == "parquet":
                df = read_parquet(filepath)
            else:
                df = read_csv(filepath)

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
                    temp_conn = duckdb.connect(":memory:")
                    temp_conn.register("source_df", parent_df)
                    filtered_df = temp_conn.query(f"SELECT * FROM source_df WHERE {condition}").pl()
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


def execute_dag(dag: Dict[str, Any], duckdb_conn: Optional[duckdb.DuckDBPyConnection] = None) -> ETLResult:
    """Convenience function to execute an ETL DAG.

    Args:
        dag: Dict representing the DAG (nodes and edges).
        duckdb_conn: Optional DuckDB connection.

    Returns:
        ETLResult instance.
    """
    executor = ETLExecutor(duckdb_conn=duckdb_conn)
    return executor.execute(dag)
