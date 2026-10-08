"""Visual chart definitions for PyBI Report Layer."""

from typing import Any, Dict, List, Optional
from pybi.core.interfaces import Visual
from pybi.dashboard.filter_context import FilterContext


class BaseVisual(Visual):
    """Base visual representation."""

    def __init__(self, visual_id: str, table_name: str, config: Dict[str, Any]):
        self.visual_id = visual_id
        self.table_name = table_name
        self.config = config

    def generate_query(self, filter_context: Optional[FilterContext] = None) -> str:
        where_clause = filter_context.to_sql_where(self.table_name) if filter_context else ""
        where_sql = f" WHERE {where_clause}" if where_clause else ""
        return f"SELECT * FROM {self.table_name}{where_sql}"


class BarChartVisual(BaseVisual):
    """Bar chart visual representation."""

    def generate_query(self, filter_context: Optional[FilterContext] = None) -> str:
        x_col = self.config.get("x", "")
        y_col = self.config.get("y", "")
        agg = (self.config.get("aggregate") or "SUM").upper()

        where_clause = filter_context.to_sql_where(self.table_name) if filter_context else ""
        where_sql = f" WHERE {where_clause}" if where_clause else ""

        if x_col and y_col:
            return f"SELECT {x_col}, {agg}({y_col}) AS {y_col} FROM {self.table_name}{where_sql} GROUP BY {x_col}"
        return super().generate_query(filter_context)


class LineChartVisual(BaseVisual):
    """Line chart visual representation."""

    def generate_query(self, filter_context: Optional[FilterContext] = None) -> str:
        x_col = self.config.get("x", "")
        y_col = self.config.get("y", "")
        agg = (self.config.get("aggregate") or "SUM").upper()

        where_clause = filter_context.to_sql_where(self.table_name) if filter_context else ""
        where_sql = f" WHERE {where_clause}" if where_clause else ""

        if x_col and y_col:
            return f"SELECT {x_col}, {agg}({y_col}) AS {y_col} FROM {self.table_name}{where_sql} GROUP BY {x_col} ORDER BY {x_col}"
        return super().generate_query(filter_context)


class TableVisual(BaseVisual):
    """Table visual representation."""

    def generate_query(self, filter_context: Optional[FilterContext] = None) -> str:
        cols = self.config.get("columns", [])
        cols_str = ", ".join(cols) if cols else "*"

        where_clause = filter_context.to_sql_where(self.table_name) if filter_context else ""
        where_sql = f" WHERE {where_clause}" if where_clause else ""

        return f"SELECT {cols_str} FROM {self.table_name}{where_sql}"


class KPIVisual(BaseVisual):
    """KPI visual representation."""

    def generate_query(self, filter_context: Optional[FilterContext] = None) -> str:
        val_col = self.config.get("value", "")
        agg = (self.config.get("aggregate") or "SUM").upper()

        where_clause = filter_context.to_sql_where(self.table_name) if filter_context else ""
        where_sql = f" WHERE {where_clause}" if where_clause else ""

        if val_col:
            return f"SELECT {agg}({val_col}) AS kpi_value FROM {self.table_name}{where_sql}"
        return super().generate_query(filter_context)
