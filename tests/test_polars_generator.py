"""Unit tests for Polars Code Generator, Transpiler, and ETL Export API endpoints."""

import os
import duckdb
import polars as pl
import pytest
from fastapi.testclient import TestClient

from pybi.api.main import app
from pybi.etl.duckdb_engine import ETLEngine
from pybi.etl.polars_generator import PolarsCodeGenerator
from pybi.schemas.etl import ETLQuery, ETLStep


@pytest.fixture
def sample_etl_query():
    return ETLQuery(
        query_name="SalesPipeline",
        source={"type": "csv", "path": "sales_data.csv"},
        steps=[
            ETLStep(
                step_id="step_1",
                step_type="filter",
                name="Filtro Età",
                params={"column": "age", "operator": ">=", "value": 18},
            ),
            ETLStep(
                step_id="step_2",
                step_type="cast",
                name="Cambio Tipo Prezzo",
                params={"column": "price", "to_type": "Float64"},
            ),
            ETLStep(
                step_id="step_3",
                step_type="rename",
                name="Rinomina Colonna",
                params={"mapping": {"category": "categoria"}},
            ),
            ETLStep(
                step_id="step_4",
                step_type="add_column",
                name="Aggiungi Concatenazione",
                params={
                    "new_column": "full_info",
                    "expr_type": "concat",
                    "concat_columns": ["name", "categoria"],
                    "separator": " - ",
                },
            ),
            ETLStep(
                step_id="step_5",
                step_type="add_column",
                name="Colonna Condizionale",
                params={
                    "new_column": "price_group",
                    "expr_type": "conditional",
                    "cond_col": "price",
                    "cond_op": ">=",
                    "cond_val": 100,
                    "val_true": "High",
                    "val_false": "Low",
                },
            ),
            ETLStep(
                step_id="step_6",
                step_type="group_by",
                name="Raggruppamento",
                params={
                    "group_columns": ["categoria"],
                    "aggregations": [{"col": "price", "agg": "sum", "alias": "totale_prezzo"}],
                },
            ),
            ETLStep(
                step_id="step_7",
                step_type="sort",
                name="Ordinamento",
                params={"column": "totale_prezzo", "descending": True},
            ),
        ],
    )


def test_polars_code_generation_syntax(sample_etl_query):
    """Test that PolarsCodeGenerator produces syntactically valid Python script."""
    generator = PolarsCodeGenerator(sample_etl_query)
    code = generator.generate_python_code()

    assert "import polars as pl" in code
    assert "def run_pipeline():" in code
    assert "df = df.filter(pl.col(\"age\") >= 18)" in code
    assert 'df = df.rename({\'category\': \'categoria\'})' in code
    assert "df.group_by(['categoria'])" in code or "df.group_by" in code
    assert "df.sort(\"totale_prezzo\", descending=True)" in code

    # Verify script compiles without syntax errors
    compiled_code = compile(code, filename="<generated_pipeline>", mode="exec")
    assert compiled_code is not None


def test_polars_vs_duckdb_data_equivalence():
    """Verify that Polars execution and DuckDB execution produce equivalent transformation outputs."""
    # Source dataset
    initial_pl_df = pl.DataFrame(
        {
            "id": [1, 2, 3, 4, 5],
            "name": ["Alice", "Bob", "Charlie", "David", "Eve"],
            "age": [17, 25, 30, 16, 40],
            "category": ["A", "B", "A", "B", "A"],
            "price": [50.0, 120.0, 80.0, 200.0, 150.0],
        }
    )

    steps = [
        {"step_id": "1", "step_type": "filter", "params": {"column": "age", "operator": ">=", "value": 18}},
        {"step_id": "2", "step_type": "rename", "params": {"mapping": {"category": "cat"}}},
        {
            "step_id": "3",
            "step_type": "add_column",
            "params": {
                "new_column": "price_cat",
                "expr_type": "conditional",
                "cond_col": "price",
                "cond_op": ">=",
                "cond_val": 100,
                "val_true": "High",
                "val_false": "Low",
            },
        },
        {
            "step_id": "4",
            "step_type": "group_by",
            "params": {
                "group_columns": ["cat"],
                "aggregations": [{"col": "price", "agg": "sum", "alias": "totale_price"}],
            },
        },
        {"step_id": "5", "step_type": "sort", "params": {"column": "totale_price", "descending": True}},
    ]

    query_dict = {"query_name": "test_query", "steps": steps}

    # 1. Execute using Polars
    polars_gen = PolarsCodeGenerator(query_dict)
    res_polars = polars_gen.execute_pipeline(initial_df=initial_pl_df)

    # 2. Execute using DuckDB
    conn = duckdb.connect(":memory:")
    conn.register("source_tbl", initial_pl_df.to_arrow())

    res_duckdb = ETLEngine.execute_steps_duckdb(
        conn=conn,
        source_table="source_tbl",
        steps=steps,
    )

    # Check column names
    assert set(res_polars.columns) == set(res_duckdb.columns)

    # Sort both by 'cat' for row order alignment check
    polars_sorted = res_polars.sort("cat")
    duckdb_sorted = res_duckdb.sort("cat")

    assert polars_sorted.to_dicts() == duckdb_sorted.to_dicts()


def test_export_python_script_api_endpoint(sample_etl_query):
    """Test the POST /api/v1/etl/export/python REST API endpoint."""
    client = TestClient(app)

    payload = sample_etl_query.model_dump()
    response = client.post("/api/v1/etl/export/python", json=payload)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/x-python")
    assert "attachment; filename=pipeline_SalesPipeline.py" in response.headers["content-disposition"]

    script_content = response.text
    assert "import polars as pl" in script_content
    assert "def run_pipeline():" in script_content
    assert "Filtro Età" in script_content


def test_export_python_script_project_api_endpoint(sample_etl_query):
    """Test the POST /api/v1/projects/{project_id}/etl/export/python REST API endpoint."""
    client = TestClient(app)

    payload = sample_etl_query.model_dump()
    response = client.post("/api/v1/projects/project_123/etl/export/python", json=payload)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/x-python")
    assert "attachment; filename=pipeline_SalesPipeline.py" in response.headers["content-disposition"]
