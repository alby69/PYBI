"""Tests for Epic 1: Semantic Layer & Data Modeling (pybi.core.semantic_model and pybi.semantic)."""

import tempfile
from pathlib import Path
import polars as pl
import pytest

from pybi.core.semantic_model import (
    Cardinality,
    JoinType,
    RLSRule,
    SemanticColumn,
    SemanticMeasure,
    SemanticModel,
    SemanticRelationship,
    SemanticTable,
)
from pybi.dashboard.binding import DataBinder
from pybi.semantic.engine import SemanticQueryResolver
from pybi.semantic.models import SemanticQueryRequest
from pybi.ui.components.widget_data import bind_widget_data


def test_semantic_model_instantiation_and_yaml_roundtrip():
    sales_tbl = SemanticTable(
        name="sales",
        source_table="sales_data",
        columns=[
            SemanticColumn(name="sale_id", column_name="sale_id", data_type="integer", is_key=True),
            SemanticColumn(name="region", column_name="region", data_type="string"),
            SemanticColumn(name="store_id", column_name="store_id", data_type="integer"),
            SemanticColumn(name="amount", column_name="amount", data_type="float"),
        ],
        measures=[
            SemanticMeasure(name="total_revenue", expression="SUM(sales.amount)", label="Total Revenue"),
            SemanticMeasure(name="avg_amount", expression="AVG(sales.amount)", label="Avg Amount"),
        ],
    )

    stores_tbl = SemanticTable(
        name="stores",
        source_table="store_dim",
        columns=[
            SemanticColumn(name="store_id", column_name="store_id", data_type="integer", is_key=True),
            SemanticColumn(name="country", column_name="country", data_type="string"),
        ],
    )

    rel = SemanticRelationship(
        from_table="sales",
        from_column="store_id",
        to_table="stores",
        to_column="store_id",
        cardinality=Cardinality.MANY_TO_ONE,
        join_type=JoinType.LEFT,
    )

    rls = RLSRule(
        name="regional_isolation",
        target_table="sales",
        filter_expression="region = '{user_allowed_region}'",
    )

    model = SemanticModel(
        name="enterprise_sales_model",
        tables=[sales_tbl, stores_tbl],
        relationships=[rel],
        rls_rules=[rls],
        default_table="sales",
    )

    assert len(model.tables) == 2
    assert model.get_table("sales") is not None
    assert model.get_table("stores") is not None

    found_col = model.find_column("stores.country")
    assert found_col is not None
    assert found_col[1].name == "country"

    found_meas = model.find_measure("total_revenue")
    assert found_meas is not None
    assert found_meas[1].expression == "SUM(sales.amount)"

    yaml_str = model.to_yaml()
    assert "enterprise_sales_model" in yaml_str
    assert "sales" in yaml_str
    assert "stores" in yaml_str

    reloaded = SemanticModel.from_yaml(yaml_str)
    assert reloaded.name == model.name
    assert len(reloaded.tables) == 2
    assert len(reloaded.relationships) == 1

    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "semantic_model.yaml"
        model.save_yaml_file(file_path)
        assert file_path.exists()

        file_reloaded = SemanticModel.load_yaml_file(file_path)
        assert file_reloaded.name == "enterprise_sales_model"


def test_semantic_query_resolver_multi_table_join():
    sales_df = pl.DataFrame({
        "sale_id": [1, 2, 3, 4],
        "store_id": [10, 10, 20, 20],
        "region": ["EU", "EU", "US", "US"],
        "amount": [100.0, 150.0, 200.0, 300.0],
    })

    stores_df = pl.DataFrame({
        "store_id": [10, 20],
        "country": ["Germany", "United States"],
    })

    sales_tbl = SemanticTable(
        name="sales",
        source_table="sales_data",
        columns=[
            SemanticColumn(name="sale_id", column_name="sale_id", data_type="integer"),
            SemanticColumn(name="store_id", column_name="store_id", data_type="integer"),
            SemanticColumn(name="region", column_name="region", data_type="string"),
            SemanticColumn(name="amount", column_name="amount", data_type="float"),
        ],
        measures=[
            SemanticMeasure(name="total_revenue", expression="SUM(sales.amount)"),
        ],
    )

    stores_tbl = SemanticTable(
        name="stores",
        source_table="store_dim",
        columns=[
            SemanticColumn(name="store_id", column_name="store_id", data_type="integer"),
            SemanticColumn(name="country", column_name="country", data_type="string"),
        ],
    )

    rel = SemanticRelationship(
        from_table="sales",
        from_column="store_id",
        to_table="stores",
        to_column="store_id",
        cardinality="*:1",
        join_type="LEFT",
    )

    model = SemanticModel(
        name="sales_model",
        tables=[sales_tbl, stores_tbl],
        relationships=[rel],
        default_table="sales",
    )

    resolver = SemanticQueryResolver()
    resolver.register_model(model)
    resolver.duckdb_conn.register("sales_data", sales_df)
    resolver.duckdb_conn.register("store_dim", stores_df)

    req = SemanticQueryRequest(
        model_name="sales_model",
        dimensions=["stores.country"],
        measures=["sales.total_revenue"],
    )

    sql = resolver.resolve_to_sql(req)
    assert "JOIN" in sql.upper()
    assert "store_dim" in sql
    assert "sales_data" in sql

    res = resolver.execute(req)
    assert res.row_count == 2
    germany_row = next(r for r in res.rows if r.get("stores_country") == "Germany")
    assert germany_row["sales_total_revenue"] == 250.0


def test_databinder_and_widget_binding_semantic_integration():
    binder = DataBinder()

    sales_df = pl.DataFrame({
        "region": ["Europe", "Europe", "US"],
        "revenue": [100.0, 200.0, 500.0],
    })

    binder.register_source("sales_tbl", sales_df)

    sales_tbl = SemanticTable(
        name="sales_tbl",
        source_table="sales_tbl",
        columns=[SemanticColumn(name="region", column_name="region", data_type="string")],
        measures=[SemanticMeasure(name="total_rev", expression="SUM(sales_tbl.revenue)")],
    )

    model = SemanticModel(
        name="sales_sem_model",
        tables=[sales_tbl],
        default_table="sales_tbl",
    )

    binder.register_semantic_model(model)

    req = SemanticQueryRequest(
        model_name="sales_sem_model",
        dimensions=["sales_tbl.region"],
        measures=["sales_tbl.total_rev"],
    )

    df_res = binder.query_semantic(req)
    assert "sales_tbl_region" in df_res.columns
    assert "sales_tbl_total_rev" in df_res.columns
    assert df_res.height == 2
