"""End-to-End dynamic RLS isolation test suite for PyBI."""

import duckdb
import polars as pl
import pytest

from pybi.core.rls_engine import RLSEngine, apply_rls_filters
from pybi.core.semantic_model import (
    SemanticColumn,
    SemanticMeasure,
    SemanticModel,
    SemanticTable,
)
from pybi.semantic.engine import SemanticQueryResolver
from pybi.semantic.models import SemanticQueryRequest


def test_e2e_rls_data_isolation_multi_tenant():
    # 1. Setup in-memory DuckDB connection and mock multi-tenant sales table
    conn = duckdb.connect(database=":memory:")
    mock_df = pl.DataFrame({
        "order_id": [1, 2, 3, 4, 5],
        "region": ["IT", "IT", "FR", "US", "DE"],
        "amount": [100.0, 150.0, 200.0, 300.0, 250.0],
        "user_id": ["u1", "u1", "u2", "u3", "u4"],
    })
    conn.register("fact_sales", mock_df)

    # 2. Define Semantic Model
    model = SemanticModel(
        name="sales_model",
        tables=[
            SemanticTable(
                name="sales",
                source_table="fact_sales",
                columns=[
                    SemanticColumn(name="order_id", column_name="order_id"),
                    SemanticColumn(name="region", column_name="region"),
                    SemanticColumn(name="user_id", column_name="user_id"),
                    SemanticColumn(name="amount", column_name="amount"),
                ],
                measures=[
                    SemanticMeasure(name="total_amount", expression='SUM("sales"."amount")')
                ],
            )
        ],
        default_table="sales",
    )

    resolver = SemanticQueryResolver(duckdb_conn=conn)
    resolver.register_model(model)

    req = SemanticQueryRequest(
        model_name="sales_model",
        dimensions=["region"],
        measures=["total_amount"],
    )

    # 3. Resolve base SQL from semantic model
    base_sql = resolver.resolve_to_sql(req)

    # 4. User 1 JWT Claims: Allowed regions = ['IT', 'FR']
    claims_u1 = {"user_id": "u1", "allowed_regions": ["IT", "FR"]}
    rls_sql_u1 = apply_rls_filters(base_sql, claims_u1, target_table="sales")

    res_u1 = conn.query(rls_sql_u1).pl()
    regions_u1 = set(res_u1["region"].to_list())

    assert "IT" in regions_u1 or "FR" in regions_u1
    assert "US" not in regions_u1 and "DE" not in regions_u1

    # 5. User 3 JWT Claims: Single region = 'US'
    claims_u3 = {"user_id": "u3", "region": "US"}
    rls_sql_u3 = apply_rls_filters(base_sql, claims_u3, target_table="sales")

    res_u3 = conn.query(rls_sql_u3).pl()
    regions_u3 = set(res_u3["region"].to_list())

    assert regions_u3 == {"US"}
