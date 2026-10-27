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


def test_execute_linear_etl_query(tmp_path):
    csv_file = tmp_path / "orders.csv"
    csv_file.write_text("region,val,status\nEU,100,active\nEU,200,inactive\nUS,300,active\nEU,50,active\n")

    query = {
        "query_name": "Orders_Query",
        "source": {"type": "csv", "path": str(csv_file)},
        "steps": [
            {
                "id": "step_1",
                "name": "Righe filtrate",
                "operation": "filter",
                "params": {"condition": "region = 'EU'"}
            },
            {
                "id": "step_2",
                "name": "Rinomina colonna",
                "operation": "rename_column",
                "params": {"mapping": {"val": "amount"}}
            },
            {
                "id": "step_3",
                "name": "Aggiungi colonna",
                "operation": "add_column",
                "params": {"new_column": "double_amount", "mode": "expression", "expression": "amount * 2"}
            }
        ]
    }

    executor = ETLExecutor()
    res = executor.execute_linear_etl(query)
    assert res.status == "success"
    assert "Orders_Query" in res.output_tables
    out_df = res.output_tables["Orders_Query"]
    assert len(out_df) == 3
    assert "double_amount" in out_df.columns
    assert "amount" in out_df.columns
    assert "val" not in out_df.columns


def test_execute_linear_etl_step_preview(tmp_path):
    csv_file = tmp_path / "data.csv"
    csv_file.write_text("a,b\n1,10\n2,20\n3,30\n")

    query = {
        "query_name": "Test_Preview",
        "source": {"type": "csv", "path": str(csv_file)},
        "steps": [
            {"id": "step_1", "name": "Filter a > 1", "operation": "filter", "params": {"condition": "a > 1"}},
            {"id": "step_2", "name": "Rename a", "operation": "rename_column", "params": {"mapping": {"a": "col_a"}}}
        ]
    }

    executor = ETLExecutor()
    # Execute up to step 1 (truncated)
    res_step1 = executor.execute_linear_etl(query, stop_at_step_index=1)
    assert res_step1.status == "success"
    df_step1 = res_step1.output_tables["Test_Preview"]
    assert len(df_step1) == 2
    assert "a" in df_step1.columns  # rename at step 2 hasn't executed yet
