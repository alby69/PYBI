"""Tests for Phase 6 Semantic Query Resolver and Dynamic RLS Engine."""

import polars as pl
import pytest

from pybi.core.query_resolver import SemanticQueryResolver
from pybi.core.rls_engine import RLSEngine, apply_rls_filters
from pybi.core.semantic_model import (
    Cardinality,
    JoinType,
    SemanticColumn,
    SemanticMeasure,
    SemanticModel,
    SemanticRelationship,
    SemanticTable,
)
from pybi.semantic.models import SemanticQueryRequest


def test_query_resolver_joins_related_tables():
    # Define Semantic Model with 2 tables and 1 relationship
    sales_tbl = SemanticTable(
        name="sales",
        source_table="fact_sales",
        columns=[
            SemanticColumn(name="customer_id", column_name="cust_id"),
            SemanticColumn(name="amount", column_name="amount"),
        ],
        measures=[
            SemanticMeasure(name="total_amount", expression='SUM("sales"."amount")')
        ],
    )
    cust_tbl = SemanticTable(
        name="customers",
        source_table="dim_customers",
        columns=[
            SemanticColumn(name="customer_id", column_name="cust_id"),
            SemanticColumn(name="region", column_name="region"),
        ],
    )
    rel = SemanticRelationship(
        from_table="sales",
        from_column="cust_id",
        to_table="customers",
        to_column="cust_id",
        cardinality=Cardinality.MANY_TO_ONE,
        join_type=JoinType.LEFT,
    )
    model = SemanticModel(
        name="sales_model",
        tables=[sales_tbl, cust_tbl],
        relationships=[rel],
        default_table="sales",
    )

    resolver = SemanticQueryResolver()
    resolver.register_model(model)

    req = SemanticQueryRequest(
        model_name="sales_model",
        dimensions=["region"],
        measures=["total_amount"],
    )

    sql = resolver.resolve_to_sql(req)

    assert "dim_customers" in sql or "customers" in sql
    assert "LEFT JOIN" in sql or "JOIN" in sql
    assert "region" in sql
    assert "total_amount" in sql or "SUM" in sql


def test_apply_rls_filters_allowed_regions():
    claims = {"user_id": "u1", "allowed_regions": ["IT", "FR"]}
    query = "SELECT * FROM sales"

    filtered = apply_rls_filters(query, claims, target_table="sales")

    assert "WHERE" in filtered
    assert "'IT'" in filtered and "'FR'" in filtered
    assert "region IN" in filtered


def test_apply_rls_filters_single_region_and_department():
    claims = {"region": "EU", "allowed_departments": ["Sales", "HR"]}
    query = "SELECT * FROM orders WHERE amount > 100"

    filtered = apply_rls_filters(query, claims)

    assert "amount > 100" in filtered
    assert "region = 'EU'" in filtered
    assert "department IN ('Sales', 'HR')" in filtered


def test_rls_engine_build_where_clause():
    engine = RLSEngine()
    claims = {"allowed_regions": ["IT"]}

    where_clause = engine.build_where_clause(claims, target_table="sales")

    assert "region IN ('IT')" in where_clause
