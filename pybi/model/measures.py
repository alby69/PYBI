"""DAX/SQL Measure Evaluation Engine for PyBI Semantic Model."""

from typing import Any, Dict, Optional
import polars as pl
from pybi.model.dax_translator import DaxTranslator
from pybi.model.engine import ModelEngine


class Measure:
    """Calculated measure definition."""

    def __init__(self, name: str, table_name: str, expression: str, description: Optional[str] = None):
        self.name = name
        self.table_name = table_name
        self.expression = expression
        self.description = description

    def to_sql_fragment(self) -> str:
        """Translate DAX-like expression into DuckDB SQL query fragment."""
        return DaxTranslator.translate(self.expression)


class MeasureEvaluator:
    """Evaluates measures against the ModelEngine."""

    def __init__(self, model_engine: ModelEngine):
        self.engine = model_engine
        self.measures: Dict[str, Measure] = {}

    def add_measure(self, measure: Measure) -> None:
        """Register a measure."""
        self.measures[measure.name] = measure
        self.engine.register_measure(measure)

    def evaluate(
        self,
        measure_name: str,
        group_by: Optional[list[str]] = None,
        where_clause: Optional[str] = None
    ) -> pl.DataFrame:
        """Evaluate a measure and return the aggregated Polars DataFrame."""
        if measure_name not in self.measures:
            raise ValueError(f"Measure '{measure_name}' not found.")

        m = self.measures[measure_name]
        sql_expr = m.to_sql_fragment()
        sql = "SELECT "
        if group_by:
            sql += ", ".join(group_by) + ", "
        sql += f"{sql_expr} AS {m.name} FROM {m.table_name}"

        if where_clause:
            sql += f" WHERE {where_clause}"

        if group_by:
            sql += " GROUP BY " + ", ".join(group_by)

        return self.engine.query(sql)
