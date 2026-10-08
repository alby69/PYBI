"""Semantic Query Resolver engine for PyBI supporting multi-table relationship resolution and DuckDB execution."""

import logging
from typing import Dict, List, Optional, Set, Tuple, Union
import duckdb
import polars as pl
import sqlglot

from pybi.core.semantic_model import (
    CoreSemanticModel,
    SemanticColumn,
    SemanticMeasure,
    SemanticModel as CoreModelType,
    SemanticTable,
)
from pybi.semantic.filter_context import build_where_clauses
from pybi.semantic.models import (
    SemanticModel,
    SemanticQueryRequest,
    SemanticQueryResponse,
)

log = logging.getLogger(__name__)


class SemanticQueryResolver:
    """Translates SemanticQueryRequest into optimized DuckDB SQL (including multi-table JOINs) and executes it."""

    def __init__(self, duckdb_conn: Optional[duckdb.DuckDBPyConnection] = None):
        self.duckdb_conn = duckdb_conn or duckdb.connect(database=":memory:")
        self.registry: Dict[str, CoreModelType] = {}

    def register_model(self, model: Union[SemanticModel, CoreModelType]) -> None:
        """Register a semantic model."""
        if isinstance(model, SemanticModel):
            core_m = model.to_core_model()
        else:
            core_m = model
        self.registry[core_m.name] = core_m

    def get_model(self, model_name: str) -> Optional[CoreModelType]:
        """Retrieve a registered semantic model by name."""
        return self.registry.get(model_name)

    def resolve_to_sql(
        self,
        request: SemanticQueryRequest,
        source_df: Optional[pl.DataFrame] = None,
    ) -> str:
        """Construct an optimized SQL query for the semantic query request with multi-table JOIN resolution."""
        model = self.get_model(request.model_name) if request.model_name else None

        if not model and request.source_table:
            # Fallback single-table model
            tbl_name = request.source_table
            model = CoreModelType(
                name="dynamic_model",
                tables=[SemanticTable(name=tbl_name, source_table=tbl_name)],
                default_table=tbl_name,
            )

        if not model or not model.tables:
            src = request.source_table or "source_table"
            model = CoreModelType(
                name="fallback_model",
                tables=[SemanticTable(name=src, source_table=src)],
                default_table=src,
            )

        # Map dimensions and measures to target tables
        referenced_tables: Set[str] = set()
        dim_targets: List[Tuple[str, str, str]] = []  # (dim_name, table_name, physical_col_name)
        meas_targets: List[Tuple[str, str, str, Optional[str]]] = []  # (meas_name, table_name, expr, agg_func)

        # Process requested dimensions
        for dim_name in request.dimensions:
            found = model.find_column(dim_name)
            if found:
                tbl, col = found
                referenced_tables.add(tbl.name)
                dim_targets.append((dim_name, tbl.name, col.column_name))
            else:
                # Default to primary table
                p_tbl = model.default_table or model.tables[0].name
                referenced_tables.add(p_tbl)
                clean_dim = dim_name.split(".")[-1]
                dim_targets.append((dim_name, p_tbl, clean_dim))

        # Process requested measures
        for meas_name in request.measures:
            found = model.find_measure(meas_name)
            if found:
                tbl, m = found
                referenced_tables.add(tbl.name)
                expr = m.expression
                if not expr and m.column_name:
                    func = (m.agg_func or "SUM").upper()
                    expr = f'{func}("{tbl.name}"."{m.column_name}")'
                elif not expr:
                    expr = f'SUM("{tbl.name}"."{m.name}")'
                meas_targets.append((meas_name, tbl.name, expr, m.agg_func))
            else:
                # Default to primary table or heuristic aggregation
                p_tbl = model.default_table or model.tables[0].name
                referenced_tables.add(p_tbl)
                clean_m = meas_name.split(".")[-1]
                m_upper = clean_m.upper()
                if any(f in m_upper for f in ("SUM(", "AVG(", "COUNT(", "MIN(", "MAX(")):
                    expr = clean_m
                else:
                    expr = f'SUM("{p_tbl}"."{clean_m}")'
                meas_targets.append((meas_name, p_tbl, expr, "SUM"))

        if not referenced_tables:
            p_tbl = model.default_table or model.tables[0].name
            referenced_tables.add(p_tbl)

        # Primary table selection
        primary_table_name = model.default_table if model.default_table in referenced_tables else next(iter(referenced_tables))
        primary_table = model.get_table(primary_table_name) or model.tables[0]

        # Build FROM clause
        from_sql = f'"{primary_table.source_table}" AS "{primary_table.name}"'

        # Build JOIN clauses for additional referenced tables
        join_sqls: List[str] = []
        joined_tables: Set[str] = {primary_table.name}

        for rel in model.relationships:
            if rel.from_table in joined_tables and rel.to_table in referenced_tables and rel.to_table not in joined_tables:
                target_tbl = model.get_table(rel.to_table)
                if target_tbl:
                    j_type = rel.join_type.upper() if isinstance(rel.join_type, str) else rel.join_type.value
                    join_sqls.append(
                        f'{j_type} JOIN "{target_tbl.source_table}" AS "{target_tbl.name}" '
                        f'ON "{rel.from_table}"."{rel.from_column}" = "{target_tbl.name}"."{rel.to_column}"'
                    )
                    joined_tables.add(target_tbl.name)
            elif rel.to_table in joined_tables and rel.from_table in referenced_tables and rel.from_table not in joined_tables:
                target_tbl = model.get_table(rel.from_table)
                if target_tbl:
                    j_type = rel.join_type.upper() if isinstance(rel.join_type, str) else rel.join_type.value
                    join_sqls.append(
                        f'{j_type} JOIN "{target_tbl.source_table}" AS "{target_tbl.name}" '
                        f'ON "{rel.to_table}"."{rel.to_column}" = "{target_tbl.name}"."{rel.from_column}"'
                    )
                    joined_tables.add(target_tbl.name)

        joins_str = (" " + " ".join(join_sqls)) if join_sqls else ""

        # Build SELECT and GROUP BY expressions
        select_exprs = []
        group_by_cols = []

        for dim_name, tbl_name, col_name in dim_targets:
            dim_expr = f'"{tbl_name}"."{col_name}"'
            alias = dim_name.replace(".", "_")
            select_exprs.append(f'{dim_expr} AS "{alias}"')
            group_by_cols.append(dim_expr)

        for meas_name, tbl_name, expr, _ in meas_targets:
            # Table-qualify simple column references in expressions if needed
            alias = meas_name.replace(".", "_")
            if expr and not ("." in expr):
                for col in (model.get_table(tbl_name).columns if model.get_table(tbl_name) else []):
                    if f'"{col.column_name}"' in expr:
                        expr = expr.replace(f'"{col.column_name}"', f'"{tbl_name}"."{col.column_name}"')
            select_exprs.append(f'{expr} AS "{alias}"')

        if not select_exprs:
            select_exprs = ["*"]

        # Build WHERE clauses
        clauses, _ = build_where_clauses(request.filters)
        # Qualify filter columns if needed
        qualified_clauses = []
        for c in clauses:
            if not ("." in c):
                qualified_clauses.append(f'"{primary_table.name}".{c}')
            else:
                qualified_clauses.append(c)

        where_sql = f" WHERE {' AND '.join(qualified_clauses)}" if qualified_clauses else ""

        # Build GROUP BY clause
        group_sql = f" GROUP BY {', '.join(group_by_cols)}" if group_by_cols else ""

        # Limit clause
        limit_sql = f" LIMIT {request.limit}" if request.limit else ""

        raw_sql = f"SELECT {', '.join(select_exprs)} FROM {from_sql}{joins_str}{where_sql}{group_sql}{limit_sql}"

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

        if source_df is not None:
            source_table = (model.default_table if model else request.source_table) or "source_table"
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
