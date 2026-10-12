"""Visual chart definitions for PyBI Report Layer."""

from typing import Any, Dict, List, Optional
from pybi.core.interfaces import Visual
from pybi.dashboard.filter_context import FilterContext


def _build_where_sql(filter_context: Optional[FilterContext], table_name: str) -> str:
    """Helper to format WHERE clause SQL fragment."""
    if not filter_context:
        return ""
    where_clause = filter_context.to_sql_where(table_name)
    if not where_clause:
        return ""
    if where_clause.startswith("WHERE"):
        return f" {where_clause}"
    return f" WHERE {where_clause}"


class BaseVisual(Visual):
    """Base visual representation."""

    def __init__(self, visual_id: str, table_name: str, config: Dict[str, Any]):
        self.visual_id = visual_id
        self.table_name = table_name
        self.config = config

    def generate_query(self, filter_context: Optional[FilterContext] = None) -> str:
        where_sql = _build_where_sql(filter_context, self.table_name)
        return f"SELECT * FROM {self.table_name}{where_sql}"


class BarChartVisual(BaseVisual):
    """Bar chart visual representation."""

    def generate_query(self, filter_context: Optional[FilterContext] = None) -> str:
        x_col = self.config.get("x", "")
        y_col = self.config.get("y", "")
        agg = (self.config.get("aggregate") or "SUM").upper()

        where_sql = _build_where_sql(filter_context, self.table_name)

        if x_col and y_col:
            return f"SELECT {x_col}, {agg}({y_col}) AS {y_col} FROM {self.table_name}{where_sql} GROUP BY {x_col}"
        return super().generate_query(filter_context)


class LineChartVisual(BaseVisual):
    """Line chart visual representation."""

    def generate_query(self, filter_context: Optional[FilterContext] = None) -> str:
        x_col = self.config.get("x", "")
        y_col = self.config.get("y", "")
        agg = (self.config.get("aggregate") or "SUM").upper()

        where_sql = _build_where_sql(filter_context, self.table_name)

        if x_col and y_col:
            return f"SELECT {x_col}, {agg}({y_col}) AS {y_col} FROM {self.table_name}{where_sql} GROUP BY {x_col} ORDER BY {x_col}"
        return super().generate_query(filter_context)


class TableVisual(BaseVisual):
    """Table visual representation."""

    def generate_query(self, filter_context: Optional[FilterContext] = None) -> str:
        cols = self.config.get("columns", [])
        cols_str = ", ".join(cols) if cols else "*"

        where_sql = _build_where_sql(filter_context, self.table_name)

        return f"SELECT {cols_str} FROM {self.table_name}{where_sql}"


class KPIVisual(BaseVisual):
    """KPI visual representation."""

    def generate_query(self, filter_context: Optional[FilterContext] = None) -> str:
        val_col = self.config.get("value", "")
        agg = (self.config.get("aggregate") or "SUM").upper()

        where_sql = _build_where_sql(filter_context, self.table_name)

        if val_col:
            return f"SELECT {agg}({val_col}) AS kpi_value FROM {self.table_name}{where_sql}"
        return super().generate_query(filter_context)
