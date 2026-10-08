"""Query Folding Compiler for PyBI ETL DAGs."""

import graphlib
from typing import Any, Dict, List, Optional, Tuple, Union
import duckdb
import polars as pl

from pybi.etl.nodes import (
    DataSourceNode,
    FilterNode,
    GroupByNode,
    JoinNode,
    OutputNode,
    PivotNode,
    SelectNode,
)


class CompilationError(Exception):
    """Exception raised when DAG compilation/folding fails."""

    pass


class ETLCompiler:
    """Compiles visual DAGs into single folded DuckDB CTE SQL queries or Polars LazyFrames."""

    def compile_to_sql(self, dag: Dict[str, Any]) -> Dict[str, str]:
        """Compile DAG into a dictionary mapping output table names to optimized SQL CTE strings.

        Args:
            dag: Dict with 'nodes' and 'edges'.

        Returns:
            Dict[str, str]: Map of output table name to complete CTE SQL query string.

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

            # Categorize
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
                    node_obj = FilterNode(node_id, data)
                    parent_sql = cte_queries.get(parents[0]) if parents else "source_df"
                    cte_queries[node_id] = node_obj.to_sql_expr(parent_sql)
                elif transform_type == "select":
                    node_obj = SelectNode(node_id, data)
                    parent_sql = cte_queries.get(parents[0]) if parents else "source_df"
                    cte_queries[node_id] = node_obj.to_sql_expr(parent_sql)
                elif transform_type in ("groupby", "group_by"):
                    node_obj = GroupByNode(node_id, data)
                    parent_sql = cte_queries.get(parents[0]) if parents else "source_df"
                    cte_queries[node_id] = node_obj.to_sql_expr(parent_sql)
                elif transform_type == "join":
                    if len(parents) < 2:
                        raise CompilationError(f"Join node '{node_id}' requires two parent inputs.")
                    node_obj = JoinNode(node_id, data)
                    left_sql = f"({cte_queries[parents[0]]})"
                    right_sql = f"({cte_queries[parents[1]]})"
                    cte_queries[node_id] = node_obj.to_sql_expr_two_tables(left_sql, right_sql)
                elif transform_type == "pivot":
                    node_obj = PivotNode(node_id, data)
                    parent_sql = cte_queries.get(parents[0]) if parents else "source_df"
                    cte_queries[node_id] = node_obj.to_sql_expr(parent_sql)

            elif category in ("Output", "output"):
                node_obj = OutputNode(node_id, data)
                table_name = data.get("table_name") or f"output_{node_id}"
                if parents:
                    parent_id = parents[0]
                    # Assemble CTE query chain
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
