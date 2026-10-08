"""Tests for Semantic Data Model and ModelEngine."""

import polars as pl
import pytest
from pybi.model import Measure, MeasureEvaluator, ModelEngine


def test_model_engine_registration_and_query():
    df = pl.DataFrame({
        "region": ["EU", "EU", "US"],
        "sales": [100.0, 200.0, 300.0]
    })

    engine = ModelEngine()
    table = engine.register_dataframe("sales_table", df)

    assert table.name == "sales_table"
    assert len(table.columns) == 2
    assert "sales_table" in engine.list_tables()

    result = engine.query("SELECT region, SUM(sales) as total_sales FROM sales_table GROUP BY region ORDER BY region")
    assert len(result) == 2
    assert result["total_sales"].to_list() == [300.0, 300.0]


def test_measure_evaluator():
    df = pl.DataFrame({
        "region": ["EU", "EU", "US"],
        "sales": [100.0, 200.0, 300.0]
    })

    engine = ModelEngine()
    engine.register_dataframe("sales_table", df)

    evaluator = MeasureEvaluator(engine)
    measure = Measure(name="TotalSales", table_name="sales_table", expression="SUM(sales)")
    evaluator.add_measure(measure)

    res = evaluator.evaluate("TotalSales", group_by=["region"])
    assert "TotalSales" in res.columns
    assert len(res) == 2
