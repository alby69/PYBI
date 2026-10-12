"""Query Folding Compiler for PyBI ETL DAGs."""

import graphlib
import logging
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import duckdb
import ibis
import ibis.expr.types as ir
import polars as pl

from pybi.core.exceptions import CompilationError, FoldingError
from pybi.etl.nodes import (
    DataSourceNode,
    FilterNode,
    GroupByNode,
    JoinNode,
    OutputNode,
    PivotNode,
    SelectNode,
)

log = logging.getLogger(__name__)


class ETLCompiler:
    """Compiles visual DAGs or sequence of ETLNodes into folded DuckDB CTE SQL queries using Ibis."""

    def __init__(self, backend: str = "duckdb", ibis_con: Optional[Any] = None):
        self.backend = backend
        self._con = ibis_con or ibis.duckdb.connect()
        self._tmp_counter = 0

    def compile(self, dag: Sequence[Any], source_expr: ir.Table) -> str:
        """Compile a topologically-sorted sequence of ETLNodes into a single SQL string using Ibis.

        Args:
            dag: Sequence of ETLNode instances.
            source_expr: The initial Ibis Table expression.

        Returns:
            A single optimized SQL string.

        Raises:
            CompilationError: If DAG translation or compilation fails.
        """
        current_expr = source_expr

        for node in dag:
            if hasattr(node, "validate"):
                errs = node.validate()
                if errs:
                    raise CompilationError(f"Node '{getattr(node, 'node_id', 'unknown')}' validation failed: {errs}")

            is_foldable = getattr(node, "foldable", True)

            if is_foldable:
                try:
                    current_expr = node.to_ibis_expr(current_expr)
                except Exception as e:
                    node_id = getattr(node, "node_id", "unknown")
                    raise FoldingError(f"Node '{node_id}' failed to fold into Ibis SQL: {e}") from e
            else:
                node_id = getattr(node, "node_id", "unknown")
                log.warning(
                    f"⚠️ Folding chain broken at node '{node_id}': materializing intermediate result"
                )
                try:
                    # Materialize upstream expression
                    intermediate_res = self._con.execute(current_expr)
                    if hasattr(intermediate_res, "to_polars"):
                        pl_df = intermediate_res.to_polars()
                    elif isinstance(intermediate_res, pl.DataFrame):
                        pl_df = intermediate_res
                    else:
                        pl_df = pl.DataFrame(intermediate_res)

                    # Execute non-foldable custom transformation
                    transform_fn = getattr(node, "transform_fn", None)
                    if not callable(transform_fn):
                        raise CompilationError(f"Node '{node_id}' is non-foldable but lacks a callable transform_fn.")

                    result_df = transform_fn(pl_df)
                    if not isinstance(result_df, pl.DataFrame):
                        result_df = pl.DataFrame(result_df)

                    tmp_table_name = f"_pybi_tmp_{node_id}_{self._tmp_counter}"
                    self._tmp_counter += 1

                    if hasattr(self._con, "con") and hasattr(self._con.con, "register"):
                        self._con.con.register(tmp_table_name, result_df)
                    elif hasattr(self._con, "register"):
                        self._con.register(tmp_table_name, result_df)
                    else:
                        self._con.create_table(tmp_table_name, result_df.to_pandas(), overwrite=True)

                    current_expr = self._con.table(tmp_table_name)
                except Exception as e:
                    raise CompilationError(f"Materialization at node '{node_id}' failed: {e}") from e

        try:
            return ibis.to_sql(current_expr, dialect=self.backend)
        except Exception as e:
            raise CompilationError(f"Ibis SQL generation failed: {e}") from e

    def compile_to_sql(self, dag: Dict[str, Any]) -> Dict[str, str]:
        """Compile DAG dict (nodes and edges) into a mapping of output table names to SQL strings.

        Args:
            dag: Dict with 'nodes' and 'edges'.

        Returns:
            Dict[str, str]: Map of output table name to SQL query string.

        Raises:
            CompilationError: If compilation fails or cycle is detected.
        """
        nodes = dag.get("nodes", [])
        edges = dag.get("edges", [])

        if not nodes:
            return {}

        node_map = {n["id"]: n for n in nodes}
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
            raise CompilationError(f"DAG compilation failed due to cycle: {err}")

        cte_queries: Dict[str, str] = {}
        output_queries: Dict[str, str] = {}

        for node_id in execution_order:
            node = node_map[node_id]
            data = node.get("data", {})
            node_type = (
                data.get("node_type")
                or node.get("node_type")
                or data.get("type")
                or node.get("type")
            )
            parents = parents_map[node_id]

            category = self._classify_category(node, node_type)

            if category in ("DataSource", "source"):
                node_obj = DataSourceNode(node_id, data)
                errors = node_obj.validate()
                if errors:
                    raise CompilationError("; ".join(errors))
                cte_queries[node_id] = node_obj.to_sql_expr()

            elif category in ("Transform", "transform"):
                transform_type = data.get("transform_type") or data.get("action") or "filter"
                if transform_type == "filter":
                    node_obj = FilterNode(node_id, data=data)
                    parent_sql = cte_queries.get(parents[0]) if parents else "source_df"
                    cte_queries[node_id] = node_obj.to_sql_expr(parent_sql)
                elif transform_type == "select":
                    node_obj = SelectNode(node_id, data=data)
                    parent_sql = cte_queries.get(parents[0]) if parents else "source_df"
                    cte_queries[node_id] = node_obj.to_sql_expr(parent_sql)
                elif transform_type in ("groupby", "group_by"):
                    node_obj = GroupByNode(node_id, data=data)
                    parent_sql = cte_queries.get(parents[0]) if parents else "source_df"
                    cte_queries[node_id] = node_obj.to_sql_expr(parent_sql)
                elif transform_type == "join":
                    if len(parents) < 2:
                        raise CompilationError(f"Join node '{node_id}' requires two parent inputs.")
                    node_obj = JoinNode(node_id, data=data)
                    left_sql = f"({cte_queries[parents[0]]})"
                    right_sql = f"({cte_queries[parents[1]]})"
                    cte_queries[node_id] = node_obj.to_sql_expr_two_tables(left_sql, right_sql)
                elif transform_type == "pivot":
                    node_obj = PivotNode(node_id, data=data)
                    parent_sql = cte_queries.get(parents[0]) if parents else "source_df"
                    cte_queries[node_id] = node_obj.to_sql_expr(parent_sql)

            elif category in ("Output", "output"):
                node_obj = OutputNode(node_id, data=data)
                table_name = data.get("table_name") or f"output_{node_id}"
                if parents:
                    parent_id = parents[0]
                    cte_chain = f"WITH {node_id}_cte AS ({cte_queries[parent_id]})\nSELECT * FROM {node_id}_cte"
                    output_queries[table_name] = cte_chain

        return output_queries

    def _classify_category(self, node: Dict[str, Any], node_type: Optional[str]) -> str:
        label = node.get("label", node.get("data", {}).get("label", ""))
        if not node_type or node_type in ("input", "default", "output"):
            if node_type == "input" or any(k in label for k in ("Source", "CSV", "Parquet", "PostgreSQL", "read_")):
                return "DataSource"
            elif node_type == "output" or any(k in label for k in ("Output", "Table", "Save")):
                return "Output"
            else:
                return "Transform"
        return node_type
