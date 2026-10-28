"""Synchronisation helpers between ETL query outputs and the project semantic model."""

import logging
from typing import Dict, List, Optional

import polars as pl

from pybi.core.semantic_model import (
    SemanticColumn,
    SemanticMeasure,
    SemanticModel,
    SemanticTable,
)
from pybi.core.storage import default_storage

log = logging.getLogger(__name__)


def _dtype_to_data_type(dtype: object) -> str:
    """Map a Polars dtype to the data types used by the semantic model."""
    name = str(dtype).lower()
    if any(token in name for token in ("int", "uint", "decimal", "float", "double")):
        return "number"
    if "bool" in name:
        return "boolean"
    if "date" in name or "time" in name:
        return "datetime"
    return "string"


def _columns_from_dataframe(df: pl.DataFrame) -> List[SemanticColumn]:
    """Build semantic columns from a Polars DataFrame schema."""
    columns: List[SemanticColumn] = []
    for col_name, dtype in df.schema.items():
        columns.append(
            SemanticColumn(
                name=col_name,
                column_name=col_name,
                data_type=_dtype_to_data_type(dtype),
            )
        )
    return columns


def _default_measures(columns: List[SemanticColumn]) -> List[SemanticMeasure]:
    """Create default SUM measures for numeric columns."""
    measures: List[SemanticMeasure] = []
    for col in columns:
        if col.data_type == "number" and not col.is_key:
            measures.append(
                SemanticMeasure(
                    name=f"sum_{col.name}",
                    expression=f"SUM({col.column_name})",
                    agg_func="SUM",
                    label=f"Sum of {col.name}",
                )
            )
    return measures


def _merge_table(model: SemanticModel, table_name: str, df: pl.DataFrame) -> bool:
    """Add or refresh a semantic table from a dataframe schema.

    Args:
        model: Semantic model to mutate.
        table_name: Name of the ETL output table.
        df: Dataframe produced by the ETL query.

    Returns:
        bool: True when the model definition changed.
    """
    if not table_name or df is None:
        return False

    new_columns = _columns_from_dataframe(df)
    if not new_columns:
        return False

    existing = model.get_table(table_name)
    if existing is None:
        model.tables.append(
            SemanticTable(
                name=table_name,
                source_table=table_name,
                columns=new_columns,
                measures=_default_measures(new_columns),
            )
        )
        return True

    existing_by_name = {col.name: col for col in existing.columns}
    changed = False
    for col in new_columns:
        current = existing_by_name.get(col.name)
        if current is None:
            existing.columns.append(col)
            changed = True
        elif current.data_type != col.data_type:
            current.data_type = col.data_type
            changed = True
    return changed


def sync_etl_outputs_into_model(
    project_id: str,
    model: Optional[SemanticModel] = None,
) -> SemanticModel:
    """Execute the project ETL query and merge its output schema into the model."""
    if model is None:
        model = SemanticModel(
            name=f"{project_id}_semantic_model", tables=[], relationships=[], rls_rules=[]
        )

    try:
        dag = default_storage.load_etl_dag(project_id) or {}
    except Exception as err:  # pragma: no cover - defensive
        log.warning("Unable to load ETL DAG for project %s: %s", project_id, err)
        return model

    has_linear = bool(dag.get("steps")) or (
        isinstance(dag.get("source"), dict) and bool(dag.get("source"))
    )
    has_nodes = bool(dag.get("nodes"))
    if not has_linear and not has_nodes:
        return model

    from pybi.etl.executor import ETLExecutor

    try:
        data_dir = default_storage.get_project_data_dir(project_id)
    except Exception:  # pragma: no cover - defensive
        data_dir = None

    try:
        executor = ETLExecutor(base_dir=data_dir)
        result = executor.execute(dag)
    except Exception as err:
        log.warning("Unable to execute ETL DAG for project %s: %s", project_id, err)
        return model

    for table_name, df in (result.output_tables or {}).items():
        _merge_table(model, table_name, df)

    return model
