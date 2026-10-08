"""Semantic Query Resolver engine for PyBI using DuckDB and SQLGlot."""

import logging
from typing import Dict, Optional, Union
import duckdb
import polars as pl
import sqlglot

from pybi.semantic.filter_context import build_where_clauses
from pybi.semantic.models import (
    Dimension,
    Measure,
    SemanticModel,
    SemanticQueryRequest,
    SemanticQueryResponse,
)

log = logging.getLogger(__name__)


class SemanticQueryResolver:
    """Translates SemanticQueryRequest into optimized DuckDB SQL and executes it."""

    def __init__(self, duckdb_conn: Optional[duckdb.DuckDBPyConnection] = None):
        self.duckdb_conn = duckdb_conn or duckdb.connect(database=":memory:")
        self.registry: Dict[str, SemanticModel] = {}

    def register_model(self, model: SemanticModel) -> None:
        """Register a semantic model."""
        self.registry[model.name] = model

    def get_model(self, model_name: str) -> Optional[SemanticModel]:
        """Retrieve a registered semantic model by name."""
        return self.registry.get(model_name)

    def resolve_to_sql(
        self,
        request: SemanticQueryRequest,
        source_df: Optional[pl.DataFrame] = None,
    ) -> str:
        """Construct an optimized SQL query for the semantic query request."""
        model = self.get_model(request.model_name) if request.model_name else None

        source_table = request.source_table
        if model:
            source_table = model.source_table

        if not source_table:
            source_table = "source_table"

        dim_map: Dict[str, Dimension] = {}
        meas_map: Dict[str, Measure] = {}

        if model:
            dim_map = {d.name: d for d in model.dimensions}
            meas_map = {m.name: m for m in model.measures}

        # Build SELECT expressions
        select_exprs = []
        group_by_cols = []

        for dim_name in request.dimensions:
            if dim_name in dim_map:
                col = dim_map[dim_name].column_name
            else:
                col = dim_name
            select_exprs.append(f'"{col}"')
            group_by_cols.append(f'"{col}"')

        for meas_name in request.measures:
            if meas_name in meas_map:
                m = meas_map[meas_name]
                if m.expression and ("(" in m.expression or " " in m.expression):
                    expr_sql = m.expression
                elif m.column_name:
                    func = (m.agg_func or "SUM").upper()
                    expr_sql = f'{func}("{m.column_name}")'
                else:
                    expr_sql = f'SUM("{m.name}")'
                select_exprs.append(f"{expr_sql} AS \"{m.name}\"")
            else:
                # Fallback heuristics if simple measure/column name passed
                meas_upper = meas_name.upper()
                if any(f in meas_upper for f in ("SUM(", "AVG(", "COUNT(", "MIN(", "MAX(")):
                    select_exprs.append(f'{meas_name} AS "{meas_name}"')
                else:
                    select_exprs.append(f'SUM("{meas_name}") AS "{meas_name}"')

        if not select_exprs:
            select_exprs = ["*"]

        # Build WHERE clauses
        clauses, _ = build_where_clauses(request.filters)
        where_sql = f" WHERE {' AND '.join(clauses)}" if clauses else ""

        # Build GROUP BY clause
        group_sql = f" GROUP BY {', '.join(group_by_cols)}" if group_by_cols else ""

        # Limit clause
        limit_sql = f" LIMIT {request.limit}" if request.limit else ""

        raw_sql = f"SELECT {', '.join(select_exprs)} FROM \"{source_table}\"{where_sql}{group_sql}{limit_sql}"

        # Transpile & optimize with SQLGlot
        try:
            transpiled_sql = sqlglot.transpile(raw_sql, read="duckdb", write="duckdb", pretty=True)[0]
            return transpiled_sql
        except Exception as e:
            log.warning(f"SQLGlot transpilation notice: {e}. Using raw generated SQL.")
            return raw_sql

    def execute(
        self,
        request: SemanticQueryRequest,
        source_df: Optional[pl.DataFrame] = None,
    ) -> SemanticQueryResponse:
        """Execute a semantic query and return a SemanticQueryResponse."""
        model = self.get_model(request.model_name) if request.model_name else None
        source_table = (model.source_table if model else request.source_table) or "source_table"

        if source_df is not None:
            self.duckdb_conn.register(source_table, source_df)

        sql = self.resolve_to_sql(request, source_df=source_df)

        res_df = self.duckdb_conn.execute(sql).pl()

        rows = res_df.to_dicts()
        columns = res_df.columns

        return SemanticQueryResponse(
            columns=columns,
            rows=rows,
            generated_sql=sql,
            row_count=len(rows),
        )
