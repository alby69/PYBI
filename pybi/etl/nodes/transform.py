"""Transformation ETL nodes implementation."""

from typing import Any, Dict, List, Optional
import polars as pl
from .base import BaseETLNode


def _format_input_table(input_table: str) -> str:
    """Format input_table for SQL FROM clause, wrapping subqueries in parentheses."""
    trimmed = input_table.strip()
    if trimmed.upper().startswith("SELECT") and not (trimmed.startswith("(") and trimmed.endswith(")")):
        return f"({trimmed})"
    return trimmed


class FilterNode(BaseETLNode):
    """Filter rows transformation node."""

    def validate(self) -> List[str]:
        condition = self.data.get("condition") or self.data.get("predicate")
        if not condition:
            return [f"Filter node '{self.node_id}' missing filter condition."]
        return []

    def to_sql_expr(self, input_table: str) -> str:
        condition = self.data.get("condition") or self.data.get("predicate")
        table_expr = _format_input_table(input_table)
        return f"SELECT * FROM {table_expr} WHERE {condition}"


class SelectNode(BaseETLNode):
    """Select columns transformation node."""

    def validate(self) -> List[str]:
        cols = self.data.get("columns", [])
        if not cols:
            return [f"Select node '{self.node_id}' missing selected columns."]
        return []

    def to_sql_expr(self, input_table: str) -> str:
        cols = self.data.get("columns", [])
        if isinstance(cols, str):
            cols = [c.strip() for c in cols.split(",") if c.strip()]
        cols_str = ", ".join(cols) if cols else "*"
        table_expr = _format_input_table(input_table)
        return f"SELECT {cols_str} FROM {table_expr}"


class GroupByNode(BaseETLNode):
    """Group by transformation node."""

    def validate(self) -> List[str]:
        group_by = self.data.get("group_by") or self.data.get("by") or []
        if not group_by:
            return [f"GroupBy node '{self.node_id}' missing grouping columns."]
        return []

    def to_sql_expr(self, input_table: str) -> str:
        group_cols = self.data.get("group_by") or self.data.get("by") or []
        if isinstance(group_cols, str):
            group_cols = [c.strip() for c in group_cols.split(",") if c.strip()]
        group_str = ", ".join(group_cols)

        aggs = self.data.get("aggregations", {})
        agg_exprs = []
        if isinstance(aggs, dict):
            for col_name, func in aggs.items():
                agg_exprs.append(f"{func.upper()}({col_name}) AS {col_name}_{func}")
        elif isinstance(aggs, str):
            for pair in aggs.split(","):
                if ":" in pair:
                    col_name, func = pair.split(":", 1)
                    agg_exprs.append(f"{func.strip().upper()}({col_name.strip()}) AS {col_name.strip()}_{func.strip()}")

        select_cols = group_str
        if agg_exprs:
            select_cols = f"{group_str}, {', '.join(agg_exprs)}"

        table_expr = _format_input_table(input_table)
        return f"SELECT {select_cols} FROM {table_expr} GROUP BY {group_str}"


class JoinNode(BaseETLNode):
    """Join transformation node."""

    def validate(self) -> List[str]:
        how = (self.data.get("how") or "inner").lower()
        if how != "cross":
            left_on = self.data.get("left_on") or self.data.get("left_column")
            right_on = self.data.get("right_on") or self.data.get("right_column")
            if not left_on or not right_on:
                return [f"Join node '{self.node_id}' missing left_on or right_on keys."]
        return []

    def to_sql_expr_two_tables(self, left_table: str, right_table: str) -> str:
        how = (self.data.get("how") or "inner").upper()
        left_expr = _format_input_table(left_table)
        right_expr = _format_input_table(right_table)
        if how == "CROSS":
            return f"SELECT * FROM {left_expr} CROSS JOIN {right_expr}"

        left_on = self.data.get("left_on") or self.data.get("left_column") or []
        right_on = self.data.get("right_on") or self.data.get("right_column") or []
        if isinstance(left_on, str):
            left_on = [c.strip() for c in left_on.split(",") if c.strip()]
        if isinstance(right_on, str):
            right_on = [c.strip() for c in right_on.split(",") if c.strip()]

        left_alias = "left_tbl"
        right_alias = "right_tbl"
        on_conditions = [f"{left_alias}.{l} = {right_alias}.{r}" for l, r in zip(left_on, right_on)]
        on_clause = " AND ".join(on_conditions)

        return f"SELECT * FROM {left_expr} AS {left_alias} {how} JOIN {right_expr} AS {right_alias} ON {on_clause}"


class PivotNode(BaseETLNode):
    """Pivot transformation node."""

    def validate(self) -> List[str]:
        on = self.data.get("on")
        if not on:
            return [f"Pivot node '{self.node_id}' missing pivot-on 'on' columns."]
        return []

    def to_sql_expr(self, input_table: str) -> str:
        index_cols = self.data.get("index") or []
        on_cols = self.data.get("on") or []
        vals = self.data.get("values") or []
        agg_fn = (self.data.get("aggregate_function") or "sum").upper()

        if isinstance(index_cols, str):
            index_cols = [c.strip() for c in index_cols.split(",") if c.strip()]
        if isinstance(on_cols, str):
            on_cols = [c.strip() for c in on_cols.split(",") if c.strip()]
        if isinstance(vals, str):
            vals = [c.strip() for c in vals.split(",") if c.strip()]

        on_str = ", ".join(on_cols)
        val_str = ", ".join(vals) if vals else "*"
        index_str = f"USING FIRST({', '.join(index_cols)})" if index_cols else ""
        table_expr = _format_input_table(input_table)

        return f"PIVOT {table_expr} ON {on_str} USING {agg_fn}({val_str}) {index_str}".strip()
