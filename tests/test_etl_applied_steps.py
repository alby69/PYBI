"""Unit and integration tests for ETL transform applied_steps sequential execution."""

import polars as pl
import pytest

from pybi.etl.executor import ETLExecutor, execute_dag
from pybi.etl.nodes.transform import FilterNode


def test_filter_node_applied_steps_execution():
    df = pl.DataFrame({
        "region": ["EU", "EU", "US", "US", "EU"],
        "amount": [150, 50, 200, 80, 120]
    })

    node = FilterNode(
        node_id="filter_1",
        applied_steps=[
            {
                "id": "step_1",
                "type": "condition",
                "description": "Filter region = 'EU'",
                "config": {"condition": "region = 'EU'"}
            },
            {
                "id": "step_2",
                "type": "condition",
                "description": "Filter amount > 100",
                "config": {"condition": "amount > 100"}
            }
        ]
    )

    res_df = node.execute(df)
    assert len(res_df) == 2
    assert set(res_df["amount"].to_list()) == {150, 120}


def test_execute_dag_with_applied_steps(tmp_path):
    csv_file = tmp_path / "sales.csv"
    csv_file.write_text("region,amount\nEU,150\nEU,50\nUS,200\nUS,80\nEU,120\n")

    dag = {
        "nodes": [
            {
                "id": "node_1",
                "type": "input",
                "label": "sales.csv",
                "data": {"node_type": "DataSource", "source_type": "csv", "file_path": str(csv_file)}
            },
            {
                "id": "node_2",
                "type": "transform",
                "label": "Filter Node",
                "data": {
                    "node_type": "Transform",
                    "transform_type": "filter",
                    "applied_steps": [
                        {"id": "s1", "type": "condition", "config": {"condition": "region = 'EU'"}},
                        {"id": "s2", "type": "condition", "config": {"condition": "amount > 100"}}
                    ]
                }
            }
        ],
        "edges": [
            {"id": "e1-2", "source": "node_1", "target": "node_2"}
        ]
    }

    result = execute_dag(dag)
    assert result.status == "success"
    out_df = result.dataframes["node_2"]
    assert len(out_df) == 2
    assert sorted(out_df["amount"].to_list()) == [120, 150]
