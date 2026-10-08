"""Transformation ETL nodes implementation."""

import re
from typing import Any, Dict, List, Optional
import ibis.expr.types as ir
import polars as pl
from pybi.core.exceptions import ValidationError
from .base import BaseETLNode


def _format_input_table(input_table: str) -> str:
    """Format input_table for SQL FROM clause, wrapping subqueries in parentheses."""
    trimmed = input_table.strip()
    if trimmed.upper().startswith("SELECT") and not (trimmed.startswith("(") and trimmed.endswith(")")):
        return f"({trimmed})"
    return trimmed


def _parse_condition(cond: str) -> tuple[Optional[str], Optional[str], Any]:
    cond = cond.strip()
    for op in (">=", "<=", "!=", "==", "=", ">", "<"):
        if op in cond:
            parts = cond.split(op, 1)
            c = parts[0].strip()
            v_str = parts[1].strip()
            if (v_str.startswith("'") and v_str.endswith("'")) or (v_str.startswith('"') and v_str.endswith('"')):
                v = v_str[1:-1]
            else:
                try:
                    v = int(v_str) if v_str.isdigit() else float(v_str)
                except ValueError:
                    v = v_str
            return c, op, v
    return None, None, None


class FilterNode(BaseETLNode):
    """Filter rows transformation node."""

    def __init__(
        self,
        node_id: str,
        column: Optional[str] = None,
        operator: Optional[str] = None,
        value: Any = None,
        data: Optional[Dict[str, Any]] = None,
    ):
        d = data.copy() if data else {}
        if column is not None:
            d["column"] = column
        if operator is not None:
            d["operator"] = operator
        if value is not None:
            d["value"] = value
        super().__init__(node_id, d)
        self.column = self.data.get("column")
        self.operator = self.data.get("operator")
        self.value = self.data.get("value")

    def validate(self) -> List[str]:
        condition = self.data.get("condition") or self.data.get("predicate")
        if not condition and not (self.column and self.operator and self.value is not None):
            return [f"Filter node '{self.node_id}' requires filter column/operator/value or condition."]
        return []

    def to_ibis_expr(self, input_expr: ir.Table) -> ir.Table:
        column = self.column or self.data.get("column")
        operator = self.operator or self.data.get("operator")
        value = self.value if self.value is not None else self.data.get("value")

        if not column or not operator:
            cond = self.data.get("condition") or self.data.get("predicate")
            if cond:
                c, op, v = _parse_condition(cond)
                if c and op:
                    column, operator, value = c, op, v

        if column and operator:
            col = input_expr[column]
            ops = {
                ">": col > value,
                "<": col < value,
                "==": col == value,
                "=": col == value,
                "!=": col != value,
                ">=": col >= value,
                "<=": col <= value,
            }
            if operator not in ops:
                raise ValidationError(f"Unsupported operator: {operator}")
            return input_expr.filter(ops[operator])

        return input_expr

    def to_sql_expr(self, input_table: str) -> str:
        condition = self.data.get("condition") or self.data.get("predicate")
        if not condition and self.column and self.operator:
            val_str = f"'{self.value}'" if isinstance(self.value, str) else str(self.value)
            op_sql = "=" if self.operator == "==" else self.operator
            condition = f"{self.column} {op_sql} {val_str}"
        table_expr = _format_input_table(input_table)
        return f"SELECT * FROM {table_expr} WHERE {condition}" if condition else f"SELECT * FROM {table_expr}"


class SelectNode(BaseETLNode):
    """Select columns transformation node."""

    def __init__(
        self,
        node_id: str,
        columns: Optional[List[str] | str] = None,
        data: Optional[Dict[str, Any]] = None,
    ):
        d = data.copy() if data else {}
        if columns is not None:
            d["columns"] = columns
        super().__init__(node_id, d)
        cols = self.data.get("columns", [])
        if isinstance(cols, str):
            cols = [c.strip() for c in cols.split(",") if c.strip()]
        self.columns = cols

    def validate(self) -> List[str]:
        if not self.columns:
            return [f"Select node '{self.node_id}' missing selected columns."]
        return []

    def to_ibis_expr(self, input_expr: ir.Table) -> ir.Table:
        if self.columns:
            return input_expr.select(self.columns)
        return input_expr

    def to_sql_expr(self, input_table: str) -> str:
        cols_str = ", ".join(self.columns) if self.columns else "*"
        table_expr = _format_input_table(input_table)
        return f"SELECT {cols_str} FROM {table_expr}"


SelectColumnsNode = SelectNode


class GroupByNode(BaseETLNode):
    """Group by transformation node."""

    def __init__(
        self,
        node_id: str,
        group_cols: Optional[List[str]] = None,
        agg_col: Optional[str] = None,
        agg_func: Optional[str] = None,
        output_alias: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ):
        d = data.copy() if data else {}
        if group_cols is not None:
            d["group_by"] = group_cols
        if agg_col is not None:
            d["agg_col"] = agg_col
        if agg_func is not None:
            d["agg_func"] = agg_func
        if output_alias is not None:
            d["output_alias"] = output_alias

        super().__init__(node_id, d)
        g_cols = self.data.get("group_by") or self.data.get("by") or []
        if isinstance(g_cols, str):
            g_cols = [c.strip() for c in g_cols.split(",") if c.strip()]
        self.group_cols = g_cols
        self.agg_col = self.data.get("agg_col")
        self.agg_func = self.data.get("agg_func")
        self.output_alias = self.data.get("output_alias")

    def validate(self) -> List[str]:
        if not self.group_cols and not self.data.get("group_by") and not self.data.get("by"):
            return [f"GroupBy node '{self.node_id}' missing grouping columns."]
        return []

    def to_ibis_expr(self, input_expr: ir.Table) -> ir.Table:
        group_cols = self.group_cols or self.data.get("group_by") or self.data.get("by") or []
        if isinstance(group_cols, str):
            group_cols = [c.strip() for c in group_cols.split(",") if c.strip()]

        if self.agg_col and self.agg_func:
            agg_func_lower = self.agg_func.lower()
            agg_funcs = {
                "sum": input_expr[self.agg_col].sum(),
                "mean": input_expr[self.agg_col].mean(),
                "avg": input_expr[self.agg_col].mean(),
                "count": input_expr[self.agg_col].count(),
                "min": input_expr[self.agg_col].min(),
                "max": input_expr[self.agg_col].max(),
            }
            if agg_func_lower not in agg_funcs:
                raise ValidationError(f"Unsupported aggregation: {self.agg_func}")
            alias = self.output_alias or f"{self.agg_col}_{agg_func_lower}"
            return input_expr.group_by(group_cols).aggregate(**{alias: agg_funcs[agg_func_lower]})

        aggs_dict = self.data.get("aggregations", {})
        if isinstance(aggs_dict, dict) and aggs_dict:
            aggs = {}
            for col_name, func in aggs_dict.items():
                f = func.lower()
                alias = f"{col_name}_{f}" if col_name in group_cols else col_name
                if f == "sum":
                    aggs[alias] = input_expr[col_name].sum()
                elif f in ("mean", "avg"):
                    aggs[alias] = input_expr[col_name].mean()
                elif f == "count":
                    aggs[alias] = input_expr[col_name].count()
                elif f == "min":
                    aggs[alias] = input_expr[col_name].min()
                elif f == "max":
                    aggs[alias] = input_expr[col_name].max()
            return input_expr.group_by(group_cols).aggregate(**aggs)

        return input_expr.group_by(group_cols).aggregate()

    def to_sql_expr(self, input_table: str) -> str:
        group_cols = self.group_cols or self.data.get("group_by") or self.data.get("by") or []
        if isinstance(group_cols, str):
            group_cols = [c.strip() for c in group_cols.split(",") if c.strip()]
        group_str = ", ".join(group_cols)

        agg_exprs = []
        if self.agg_col and self.agg_func:
            alias = self.output_alias or f"{self.agg_col}_{self.agg_func.lower()}"
            agg_exprs.append(f"{self.agg_func.upper()}({self.agg_col}) AS {alias}")
        else:
            aggs = self.data.get("aggregations", {})
            if isinstance(aggs, dict):
                for col_name, func in aggs.items():
                    agg_exprs.append(f"{func.upper()}({col_name}) AS {col_name}_{func}")

        select_cols = group_str
        if agg_exprs:
            select_cols = f"{group_str}, {', '.join(agg_exprs)}" if group_str else ", ".join(agg_exprs)

        table_expr = _format_input_table(input_table)
        return f"SELECT {select_cols} FROM {table_expr} GROUP BY {group_str}" if group_str else f"SELECT {select_cols} FROM {table_expr}"


GroupByAggregateNode = GroupByNode


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

    def to_ibis_expr_two_tables(self, left_expr: ir.Table, right_expr: ir.Table) -> ir.Table:
        how = (self.data.get("how") or "inner").lower()
        if how == "cross":
            return left_expr.cross_join(right_expr)

        left_on = self.data.get("left_on") or self.data.get("left_column") or []
        right_on = self.data.get("right_on") or self.data.get("right_column") or []
        if isinstance(left_on, str):
            left_on = [c.strip() for c in left_on.split(",") if c.strip()]
        if isinstance(right_on, str):
            right_on = [c.strip() for c in right_on.split(",") if c.strip()]

        predicates = [left_expr[l] == right_expr[r] for l, r in zip(left_on, right_on)]
        return left_expr.join(right_expr, predicates=predicates, how=how)

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
