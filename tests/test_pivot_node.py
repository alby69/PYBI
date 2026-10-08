"""Unit tests for Pivot ETL node and ETLExecutor integration."""

import polars as pl
from pybi.etl.executor import ETLExecutor
from pybi.etl.node_factory import build_node, build_node_data, node_kind, node_values


def test_pivot_node_factory():
    values = {
        "index": "region",
        "on": "product",
        "values": "sales",
        "aggregate_function": "sum",
    }
    data = build_node_data("Pivot", values)
    assert data["node_type"] == "Transform"
    assert data["transform_type"] == "pivot"
    assert data["index"] == ["region"]
    assert data["on"] == ["product"]
    assert data["values"] == ["sales"]
    assert data["aggregate_function"] == "sum"

    node = build_node("Pivot", values, "pivot_1", {"x": 100, "y": 100})
    assert node_kind(node) == "Pivot"
    extracted = node_values(node)
    assert extracted["index"] == "region"
    assert extracted["on"] == "product"
    assert extracted["values"] == "sales"


def test_pivot_etl_executor_execution():
    executor = ETLExecutor()
    input_df = pl.DataFrame({
        "region": ["North", "North", "South", "South"],
        "product": ["A", "B", "A", "B"],
        "sales": [100, 200, 300, 400],
    })

    dag = {
        "nodes": [
            {
                "id": "source_1",
                "data": {"node_type": "DataSource", "source_type": "csv", "file_path": "dummy.csv"},
            },
            {
                "id": "pivot_1",
                "data": {
                    "node_type": "Transform",
                    "transform_type": "pivot",
                    "index": ["region"],
                    "on": ["product"],
                    "values": ["sales"],
                    "aggregate_function": "sum",
                },
            },
        ],
        "edges": [{"source": "source_1", "target": "pivot_1"}],
    }

    # Execute node directly with input dataframe
    pivoted_df, log_msg, _ = executor._execute_node(
        dag["nodes"][1], ["source_1"], {"source_1": input_df}
    )

    assert "product" not in pivoted_df.columns
    assert "A" in pivoted_df.columns
    assert "B" in pivoted_df.columns
    assert len(pivoted_df) == 2
