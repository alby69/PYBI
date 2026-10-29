import duckdb
import polars as pl
import pytest

from pybi.backend.engine.etl_engine import ETLEngine
from pybi.backend.models.etl import ETLStep


def test_sql_generation_change_type():
    step = ETLStep(
        step_id="step_1",
        step_type="change_type",
        parameters={"column": "price", "new_type": "INTEGER"}
    )
    sql = ETLEngine.build_step_clause("source_table", step)
    assert "CAST(price AS INTEGER) AS price" in sql or 'CAST("price" AS BIGINT)' in sql or 'CAST("price" AS INTEGER)' in sql or 'CAST(price AS INTEGER)' in sql


def test_sql_generation_rename_column():
    step = ETLStep(
        step_id="step_2",
        step_type="rename_column",
        parameters={"old_name": "product", "new_name": "product_name"}
    )
    sql = ETLEngine.build_step_clause("source_table", step)
    assert "RENAME (product AS product_name)" in sql or "product AS product_name" in sql or 'RENAME ("product" AS "product_name")' in sql or '"product" AS "product_name"' in sql


def test_sql_generation_filter_rows():
    step = ETLStep(
        step_id="step_3",
        step_type="filter_rows",
        parameters={"column": "category", "operator": "equals", "value": "'Electronics'"}
    )
    sql = ETLEngine.build_step_clause("source_table", step)
    assert "WHERE category = 'Electronics'" in sql or 'WHERE "category" = \'Electronics\'' in sql


def test_sql_generation_add_custom_column():
    step = ETLStep(
        step_id="step_4",
        step_type="add_custom_column",
        parameters={"new_column": "total_amount", "expression": "price * qty"}
    )
    sql = ETLEngine.build_step_clause("source_table", step)
    assert "price * qty AS total_amount" in sql or 'price * qty AS "total_amount"' in sql or '(price * qty) AS "total_amount"' in sql


def test_full_pipeline_execution_duckdb(in_memory_duckdb):
    steps = [
        ETLStep(step_id="s1", step_type="filter_rows", parameters={"column": "category", "operator": "equals", "value": "'Electronics'"}),
        ETLStep(step_id="s2", step_type="add_custom_column", parameters={"new_column": "total", "expression": "price * qty"}),
        ETLStep(step_id="s3", step_type="remove_columns", parameters={"columns": ["qty"]})
    ]

    result_df = ETLEngine.execute_steps_duckdb(
        conn=in_memory_duckdb,
        source_table="sales",
        steps=steps,
        limit=100
    )

    assert len(result_df) == 2  # Product A and Product C
    assert "total" in result_df.columns
    assert "qty" not in result_df.columns
    assert result_df.filter(pl.col("product") == "Product A")["total"][0] == 200.0


def test_preview_step_index_truncation(in_memory_duckdb):
    steps = [
        ETLStep(step_id="s1", step_type="filter_rows", parameters={"column": "price", "operator": ">", "value": "20"}),
        ETLStep(step_id="s2", step_type="remove_columns", parameters={"columns": ["sale_date"]})
    ]

    # Execute only up to step 1 (includes step 1 filter, excludes step 2 remove_columns)
    preview_step_0 = ETLEngine.execute_steps_duckdb(
        conn=in_memory_duckdb,
        source_table="sales",
        steps=steps,
        step_index=1,
        limit=100
    )

    assert "sale_date" in preview_step_0.columns  # Not removed yet
    assert len(preview_step_0) == 3               # Filter applied


def test_empty_result_set(in_memory_duckdb):
    steps = [
        ETLStep(step_id="s1", step_type="filter_rows", parameters={"column": "price", "operator": ">", "value": "999999"})
    ]
    result_df = ETLEngine.execute_steps_duckdb(
        conn=in_memory_duckdb,
        source_table="sales",
        steps=steps
    )
    assert len(result_df) == 0
    assert "product" in result_df.columns
    assert "price" in result_df.columns


def test_column_name_collision(in_memory_duckdb):
    steps = [
        ETLStep(step_id="s1", step_type="add_custom_column", parameters={"new_column": "price", "expression": "price * 2"})
    ]
    result_df = ETLEngine.execute_steps_duckdb(
        conn=in_memory_duckdb,
        source_table="sales",
        steps=steps
    )
    assert "price" in result_df.columns
    assert result_df.filter(pl.col("product") == "Product A")["price"][0] == 200.0


def test_special_characters_in_column_names(in_memory_duckdb):
    steps = [
        ETLStep(step_id="s1", step_type="add_custom_column", parameters={"new_column": "Total Price ($)", "expression": "price * qty"})
    ]
    sql = ETLEngine.to_duckdb_sql({"source": {"table": "sales"}, "steps": steps})
    assert '"Total Price ($)"' in sql
    result_df = ETLEngine.execute_steps_duckdb(
        conn=in_memory_duckdb,
        source_table="sales",
        steps=steps
    )
    assert "Total Price ($)" in result_df.columns


def test_data_type_casting_error(in_memory_duckdb):
    steps = [
        ETLStep(step_id="s1", step_type="change_type", parameters={"column": "product", "new_type": "INTEGER"})
    ]
    with pytest.raises(Exception):
        ETLEngine.execute_steps_duckdb(
            conn=in_memory_duckdb,
            source_table="sales",
            steps=steps
        )
