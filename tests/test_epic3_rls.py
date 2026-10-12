"""Tests for Epic 3: Dynamic Row-Level Security (RLS)."""

import duckdb
import polars as pl
import pytest

from pybi.auth.jwt_auth import AuthUser
from pybi.core.rls_engine import RLSEngine
from pybi.core.semantic_model import (
    CoreSemanticModel,
    RLSRule,
    SemanticColumn,
    SemanticTable,
)
from pybi.semantic.engine import SemanticQueryResolver
from pybi.semantic.models import SemanticQueryRequest


def test_rls_engine_clause_generation():
    model = CoreSemanticModel(
        name="rls_model",
        tables=[
            SemanticTable(
                name="sales",
                source_table="sales_table",
                columns=[
                    SemanticColumn(name="id", column_name="id"),
                    SemanticColumn(name="region", column_name="region"),
                ],
            )
        ],
        rls_rules=[
            RLSRule(
                name="region_isolation",
                target_table="sales",
                filter_expression="region = '{allowed_regions}'",
            )
        ],
    )

    user_eu = AuthUser(username="user_eu", role="viewer", claims={"allowed_regions": "EU"})
    clauses_eu = RLSEngine.get_rls_clauses(model, user_eu)
    assert len(clauses_eu) == 1
    assert clauses_eu[0] == '"sales".region = \'EU\''

    user_multi = AuthUser(username="user_multi", role="viewer", claims={"allowed_regions": ["EU", "US"]})
    clauses_multi = RLSEngine.get_rls_clauses(model, user_multi)
    assert len(clauses_multi) == 1
    assert "IN ('EU', 'US')" in clauses_multi[0]

    user_admin = AuthUser(username="admin", role="admin", claims={"allowed_regions": "*"})
    clauses_admin = RLSEngine.get_rls_clauses(model, user_admin)
    assert len(clauses_admin) == 0


def test_rls_query_execution_e2e():
    conn = duckdb.connect(database=":memory:")

    sales_df = pl.DataFrame({
        "id": [1, 2, 3, 4],
        "region": ["EU", "US", "EU", "APAC"],
        "amount": [100.0, 200.0, 150.0, 300.0],
    })
    conn.register("sales_table", sales_df)

    model = CoreSemanticModel(
        name="rls_e2e_model",
        tables=[
            SemanticTable(
                name="sales",
                source_table="sales_table",
                columns=[
                    SemanticColumn(name="id", column_name="id"),
                    SemanticColumn(name="region", column_name="region"),
                    SemanticColumn(name="amount", column_name="amount"),
                ],
            )
        ],
        rls_rules=[
            RLSRule(
                name="region_filter",
                target_table="sales",
                filter_expression="region = '{allowed_regions}'",
            )
        ],
        default_table="sales",
    )

    resolver = SemanticQueryResolver(duckdb_conn=conn)
    resolver.register_model(model)

    req = SemanticQueryRequest(
        model_name="rls_e2e_model",
        dimensions=["sales.region"],
        measures=["sales.amount"],
    )

    user_eu = AuthUser(username="alice", role="viewer", claims={"allowed_regions": "EU"})
    resp_eu = resolver.execute(req, auth_user=user_eu)
    assert resp_eu.row_count == 1
    assert resp_eu.rows[0]["sales_region"] == "EU"
    assert resp_eu.rows[0]["sales_amount"] == 250.0

    user_us = AuthUser(username="bob", role="viewer", claims={"allowed_regions": "US"})
    resp_us = resolver.execute(req, auth_user=user_us)
    assert resp_us.row_count == 1
    assert resp_us.rows[0]["sales_region"] == "US"
    assert resp_us.rows[0]["sales_amount"] == 200.0
