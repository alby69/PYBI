"""Unit tests for pybi.ui.components.charts module."""

import polars as pl
import pytest

from pybi.dashboard.binding import DataBinder
from pybi.ui.components.charts import BarChart, Chart, LineChart


def test_chart_creation_and_binding():
    binder = DataBinder()
    df = pl.DataFrame({
        "month": ["Jan", "Feb", "Mar"],
        "sales": [100, 150, 200]
    })
    binder.register_source("monthly_sales", df)

    chart = Chart(
        widget_id="chart_1",
        source_name="monthly_sales",
        chart_type="bar",
        x_col="month",
        y_cols=["sales"],
        title="Monthly Sales",
        binder=binder,
    )

    assert chart.widget_id == "chart_1"
    assert chart.source_name == "monthly_sales"
    assert len(chart.dataframe) == 3
    assert chart.dataframe["sales"].to_list() == [100, 150, 200]


def test_barchart_reactive_update():
    binder = DataBinder()
    df = pl.DataFrame({
        "region": ["North", "South"],
        "revenue": [500, 300]
    })
    binder.register_source("regional_data", df)

    bar = BarChart(
        widget_id="bar_1",
        source_name="regional_data",
        x_col="region",
        y_cols=["revenue"],
        title="Regional Data",
        binder=binder,
    )

    assert len(bar.dataframe) == 2

    # Reactive update via binder
    new_df = pl.DataFrame({
        "region": ["North", "South", "East"],
        "revenue": [550, 320, 410]
    })
    binder.update_source("regional_data", new_df)

    assert len(bar.dataframe) == 3
    assert bar.dataframe["revenue"].to_list() == [550, 320, 410]


def test_linechart_reactive_update():
    binder = DataBinder()
    df = pl.DataFrame({
        "time": [1, 2, 3],
        "value": [10.0, 12.5, 15.0]
    })
    binder.register_source("time_series", df)

    line = LineChart(
        widget_id="line_1",
        source_name="time_series",
        x_col="time",
        y_cols=["value"],
        title="Time Series",
        binder=binder,
    )

    assert line.chart_type == "line"
    assert len(line.dataframe) == 3

    # Update with query
    query_df = pl.DataFrame({
        "time": [2, 3],
        "value": [12.5, 15.0]
    })
    line.bind_source("time_series", query="SELECT * FROM time_series WHERE time >= 2")
    assert len(line.dataframe) == 2
