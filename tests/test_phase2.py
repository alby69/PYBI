"""Unit tests for Phase 2: Core Data Engine & Visual Binding."""

import os
import tempfile
import polars as pl
import pytest
import duckdb

from pybi.etl.connectors import read_csv, read_parquet
from pybi.etl.executor import ETLExecutor, execute_dag
from pybi.dashboard import DataBinder
from pybi.ui.components.chart_widget import ChartWidget


@pytest.fixture
def sample_csv_file():
    """Fixture creating a temporary CSV file with sample sales data."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write("id,region,product,sales,quantity\n")
        f.write("1,EU,Laptop,1200,3\n")
        f.write("2,US,Tablet,450,5\n")
        f.write("3,EU,Monitor,300,2\n")
        f.write("4,APAC,Phone,800,4\n")
        f.write("5,EU,Keyboard,100,10\n")
    filepath = f.name
    yield filepath
    if os.path.exists(filepath):
        os.remove(filepath)


@pytest.fixture
def sample_parquet_file(sample_csv_file):
    """Fixture creating a temporary Parquet file with sample data."""
    df = read_csv(sample_csv_file)
    parquet_path = sample_csv_file.replace(".csv", ".parquet")
    df.write_parquet(parquet_path)
    yield parquet_path
    if os.path.exists(parquet_path):
        os.remove(parquet_path)


def test_connectors(sample_csv_file, sample_parquet_file):
    """Test read_csv and read_parquet connectors."""
    df_csv = read_csv(sample_csv_file)
    assert isinstance(df_csv, pl.DataFrame)
    assert len(df_csv) == 5
    assert set(df_csv.columns) == {"id", "region", "product", "sales", "quantity"}

    df_parquet = read_parquet(sample_parquet_file)
    assert isinstance(df_parquet, pl.DataFrame)
    assert len(df_parquet) == 5
    assert df_parquet.equals(df_csv)


def test_etl_executor_csv_filter_output(sample_csv_file):
    """Test ETL executor with CSV source -> Filter -> DuckDB Output pipeline."""
    dag = {
        "nodes": [
            {
                "id": "n1",
                "type": "input",
                "label": f"📄 CSV Source ({sample_csv_file})",
                "data": {"node_type": "DataSource", "source_type": "csv", "file_path": sample_csv_file},
            },
            {
                "id": "n2",
                "label": "⚡ Filter Rows (region = 'EU')",
                "data": {"node_type": "Transform", "transform_type": "filter", "condition": "region = 'EU'"},
            },
            {
                "id": "n3",
                "type": "output",
                "label": "💾 DuckDB Table (filtered_sales)",
                "data": {"node_type": "Output", "table_name": "filtered_sales"},
            },
        ],
        "edges": [
            {"id": "e1-2", "source": "n1", "target": "n2"},
            {"id": "e2-3", "source": "n2", "target": "n3"},
        ],
    }

    result = execute_dag(dag)
    assert result.status == "success"
    assert "filtered_sales" in result.output_tables

    output_df = result.output_tables["filtered_sales"]
    assert len(output_df) == 3
    assert set(output_df["region"].to_list()) == {"EU"}


def test_etl_executor_groupby_transform(sample_csv_file):
    """Test ETL executor with CSV source -> Select -> GroupBy pipeline."""
    dag = {
        "nodes": [
            {
                "id": "src",
                "data": {"node_type": "DataSource", "source_type": "csv", "file_path": sample_csv_file},
            },
            {
                "id": "sel",
                "data": {"node_type": "Transform", "transform_type": "select", "columns": ["region", "sales"]},
            },
            {
                "id": "grp",
                "data": {
                    "node_type": "Transform",
                    "transform_type": "groupby",
                    "group_by": ["region"],
                    "aggregations": {"sales": "sum"},
                },
            },
            {
                "id": "out",
                "data": {"node_type": "Output", "table_name": "grouped_sales"},
            },
        ],
        "edges": [
            {"id": "e1", "source": "src", "target": "sel"},
            {"id": "e2", "source": "sel", "target": "grp"},
            {"id": "e3", "source": "grp", "target": "out"},
        ],
    }

    executor = ETLExecutor()
    result = executor.execute(dag)
    assert result.status == "success"
    assert "grouped_sales" in result.output_tables

    grouped_df = result.output_tables["grouped_sales"]
    assert len(grouped_df) == 3  # EU, US, APAC
    assert "region" in grouped_df.columns
    assert "sales" in grouped_df.columns


def test_dashboard_data_binding():
    """Test DataBinder registering sources, binding widgets, querying, and reactive updates."""
    binder = DataBinder()

    df_initial = pl.DataFrame({"category": ["A", "B", "C"], "value": [10, 20, 30]})
    binder.register_source("kpi_data", df_initial)

    updated_df_received = []

    def widget_callback(updated_df: pl.DataFrame):
        updated_df_received.append(updated_df)

    # Bind widget without query
    binder.bind_widget("w1", "kpi_data")
    data_w1 = binder.get_widget_data("w1")
    assert len(data_w1) == 3

    # Bind widget with SQL query and reactive callback
    binder.bind_widget(
        "w2",
        "kpi_data",
        query="SELECT category, value FROM kpi_data WHERE value >= 20",
        callback=widget_callback,
    )
    data_w2 = binder.get_widget_data("w2")
    assert len(data_w2) == 2
    assert data_w2["category"].to_list() == ["B", "C"]

    # Trigger reactive update
    df_new = pl.DataFrame({"category": ["A", "B", "C"], "value": [25, 35, 45]})
    binder.update_source("kpi_data", df_new)

    assert len(updated_df_received) == 1
    # All 3 rows now have value >= 20
    assert len(updated_df_received[0]) == 3


def test_chart_widget_options():
    """Test ChartWidget ECharts options construction for bar, line, and pie charts."""
    df = pl.DataFrame({"region": ["EU", "US"], "sales": [100, 200]})

    opts_bar = ChartWidget._build_options(df, "bar", "region", ["sales"], "Regional Sales")
    assert opts_bar["xAxis"]["data"] == ["EU", "US"]
    assert opts_bar["series"][0]["type"] == "bar"
    assert opts_bar["series"][0]["data"] == [100, 200]

    opts_line = ChartWidget._build_options(df, "line", "region", ["sales"], "Trend")
    assert opts_line["series"][0]["type"] == "line"

    opts_pie = ChartWidget._build_options(df, "pie", "region", ["sales"], "Breakdown")
    assert opts_pie["series"][0]["type"] == "pie"
    assert opts_pie["series"][0]["data"] == [
        {"name": "EU", "value": 100},
        {"name": "US", "value": 200},
    ]
