"""Tests for FilterContext and QueryBuilder."""

import pytest
from pybi.dashboard import FilterContext
from pybi.report import QueryBuilder


def test_filter_context_notifications():
    fc = FilterContext()
    notifications = []

    def on_change(context):
        notifications.append(len(context.filters))

    fc.subscribe(on_change)

    fc.add_filter("sales_table", "region", "EU")
    assert len(notifications) == 1
    assert notifications[0] == 1

    sql_where = fc.to_sql_where("sales_table")
    assert "region = 'EU'" in sql_where

    fc.remove_filter("sales_table", "region")
    assert len(notifications) == 2
    assert notifications[1] == 0


def test_query_builder():
    fc = FilterContext()
    fc.add_filter("sales_table", "year", 2024)

    query = QueryBuilder.build_query(
        visual_type="bar",
        visual_id="bar_1",
        table_name="sales_table",
        config={"x": "region", "y": "sales", "aggregate": "sum"},
        filter_context=fc
    )

    assert "SELECT region, SUM(sales) AS sales FROM sales_table" in query
    assert "WHERE year = 2024" in query
    assert "GROUP BY region" in query
