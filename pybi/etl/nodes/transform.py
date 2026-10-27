"""Transformation ETL nodes implementation."""

import re
from typing import Any, Dict, List, Optional
import ibis.expr.types as ir
import polars as pl
from pybi.core.exceptions import ValidationError
from pybi.etl.calculated import (
    apply_calculated_column,
    build_calculated_expression,
    quote_identifier,
)
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
    """Filter rows transformation node with sequential applied_steps support."""

    def __init__(
        self,
        node_id: str,
        column: Optional[str] = None,
        operator: Optional[str] = None,
        value: Any = None,
        data: Optional[Dict[str, Any]] = None,
        applied_steps: Optional[List[Dict[str, Any]]] = None,
    ):
        d = data.copy() if data else {}
        if column is not None:
            d["column"] = column
        if operator is not None:
            d["operator"] = operator
        if value is not None:
            d["value"] = value
        if applied_steps is not None:
            d["applied_steps"] = applied_steps
        super().__init__(node_id, d)
        self.column = self.data.get("column")
        self.operator = self.data.get("operator")
        self.value = self.data.get("value")
        self.applied_steps = self.data.get("applied_steps", [])

    def validate(self) -> List[str]:
        condition = self.data.get("condition") or self.data.get("predicate")
        applied_steps = self.data.get("applied_steps") or self.applied_steps
        if not condition and not (self.column and self.operator and self.value is not None) and not applied_steps:
            return [f"Filter node '{self.node_id}' requires filter column/operator/value, condition, or applied_steps."]
        return []

    def execute(self, df: pl.DataFrame) -> pl.DataFrame:
        """Execute node filters or applied steps sequentially on a Polars DataFrame."""
        applied_steps = self.data.get("applied_steps") or self.applied_steps
        if applied_steps:
            for step in applied_steps:
                step_type = step.get("type") or "condition"
                config = step.get("config") or {}
                cond = config.get("condition") or step.get("condition")
                if cond:
                    c, op, v = _parse_condition(cond)
                    if c and op:
                        if op in ("==", "="):
                            df = df.filter(pl.col(c) == v)
                        elif op == "!=":
                            df = df.filter(pl.col(c) != v)
                        elif op == ">":
                            df = df.filter(pl.col(c) > v)
                        elif op == "<":
                            df = df.filter(pl.col(c) < v)
                        elif op == ">=":
                            df = df.filter(pl.col(c) >= v)
                        elif op == "<=":
                            df = df.filter(pl.col(c) <= v)
            return df
        return df

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


class UnpivotNode(BaseETLNode):
    """Unpivot transformation node."""

    def __init__(
        self,
        node_id: str,
        on: Optional[List[str] | str] = None,
        index: Optional[List[str] | str] = None,
        variable_name: str = "variable",
        value_name: str = "value",
        data: Optional[Dict[str, Any]] = None,
    ):
        d = data.copy() if data else {}
        if on is not None:
            d["on"] = on
        if index is not None:
            d["index"] = index
        if variable_name:
            d["variable_name"] = variable_name
        if value_name:
            d["value_name"] = value_name
        super().__init__(node_id, d)

        def _clean_cols(v: Any) -> List[str]:
            if isinstance(v, str):
                return [c.strip() for c in v.split(",") if c.strip()]
            return list(v or [])

        self.on_cols = _clean_cols(self.data.get("on"))
        self.index_cols = _clean_cols(self.data.get("index"))
        self.variable_name = self.data.get("variable_name") or "variable"
        self.value_name = self.data.get("value_name") or "value"

    def validate(self) -> List[str]:
        if not self.on_cols:
            return [f"Unpivot node '{self.node_id}' missing unpivot columns ('on')."]
        return []

    def execute(self, df: pl.DataFrame) -> pl.DataFrame:
        idx = self.index_cols if self.index_cols else None
        return df.unpivot(
            index=idx,
            on=self.on_cols,
            variable_name=self.variable_name,
            value_name=self.value_name,
        )

    def to_ibis_expr(self, input_expr: ir.Table) -> ir.Table:
        return input_expr.pivot_longer(
            self.on_cols,
            names_to=self.variable_name,
            values_to=self.value_name,
        )

    def to_sql_expr(self, input_table: str) -> str:
        table_expr = _format_input_table(input_table)
        on_str = ", ".join(self.on_cols)
        var_name = self.variable_name
        val_name = self.value_name
        return f"UNPIVOT {table_expr} ON {on_str} INTO NAME {var_name} VALUE {val_name}"


class FillDownNode(BaseETLNode):
    """Fill down missing (NULL) values along rows transformation node."""

    def __init__(
        self,
        node_id: str,
        columns: Optional[List[str] | str] = None,
        order_by: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ):
        d = data.copy() if data else {}
        if columns is not None:
            d["columns"] = columns
        if order_by is not None:
            d["order_by"] = order_by
        super().__init__(node_id, d)

        cols = self.data.get("columns", [])
        if isinstance(cols, str):
            cols = [c.strip() for c in cols.split(",") if c.strip()]
        self.columns = list(cols or [])
        self.order_by = self.data.get("order_by")

    def validate(self) -> List[str]:
        if not self.columns:
            return [f"FillDown node '{self.node_id}' missing target columns."]
        return []

    def execute(self, df: pl.DataFrame) -> pl.DataFrame:
        if self.order_by and self.order_by in df.columns:
            df = df.sort(self.order_by)
        exprs = [pl.col(c).forward_fill() for c in self.columns]
        return df.with_columns(exprs)

    def to_sql_expr(self, input_table: str) -> str:
        table_expr = _format_input_table(input_table)
        order_clause = f"ORDER BY {self.order_by} " if self.order_by else ""
        window_spec = f"({order_clause}ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)"
        cols_str = ", ".join(self.columns)
        fill_exprs = ", ".join(
            f"LAST_VALUE({c} IGNORE NULLS) OVER {window_spec} AS {c}" for c in self.columns
        )
        return f"SELECT * EXCLUDE ({cols_str}), {fill_exprs} FROM {table_expr}"


class RenameColumnNode(BaseETLNode):
    """Rename column transformation node."""

    def __init__(
        self,
        node_id: str,
        mapping: Optional[Dict[str, str]] = None,
        column_mapping: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ):
        d = data.copy() if data else {}
        if mapping is not None:
            d["mapping"] = mapping
        if column_mapping is not None:
            d["column_mapping"] = column_mapping
        super().__init__(node_id, d)

        m = self.data.get("mapping") or {}
        if not m and self.data.get("column_mapping"):
            # Format: "old_name:new_name, old2:new2"
            raw_map = str(self.data.get("column_mapping"))
            m = {}
            for chunk in raw_map.split(","):
                if ":" in chunk:
                    old_c, new_c = chunk.split(":", 1)
                    if old_c.strip() and new_c.strip():
                        m[old_c.strip()] = new_c.strip()
        self.mapping = m  # {old_name: new_name}

    def validate(self) -> List[str]:
        if not self.mapping:
            return [f"RenameColumn node '{self.node_id}' missing column rename mapping."]
        return []

    def execute(self, df: pl.DataFrame) -> pl.DataFrame:
        return df.rename(self.mapping)

    def to_ibis_expr(self, input_expr: ir.Table) -> ir.Table:
        # Ibis Table.rename takes {new_name: old_name}
        ibis_map = {new_c: old_c for old_c, new_c in self.mapping.items()}
        return input_expr.rename(ibis_map)

    def to_sql_expr(self, input_table: str) -> str:
        table_expr = _format_input_table(input_table)
        renames = [f"{old_c} AS {new_c}" for old_c, new_c in self.mapping.items()]
        # We replace renamed columns or do a simple SELECT with alias
        # DuckDB supports RENAME clause or SELECT * RENAME (...)
        rename_clause = ", ".join(f"{old_c} AS {new_c}" for old_c, new_c in self.mapping.items())
        return f"SELECT * RENAME ({rename_clause}) FROM {table_expr}"


class CastColumnNode(BaseETLNode):
    """Cast column data types transformation node."""

    SUPPORTED_TYPES = {
        "text": "VARCHAR",
        "string": "VARCHAR",
        "varchar": "VARCHAR",
        "int": "BIGINT",
        "integer": "BIGINT",
        "bigint": "BIGINT",
        "float": "DOUBLE",
        "double": "DOUBLE",
        "numeric": "DOUBLE",
        "boolean": "BOOLEAN",
        "bool": "BOOLEAN",
        "date": "DATE",
        "timestamp": "TIMESTAMP",
        "datetime": "TIMESTAMP",
    }

    POLARS_TYPES = {
        "VARCHAR": pl.Utf8,
        "BIGINT": pl.Int64,
        "DOUBLE": pl.Float64,
        "BOOLEAN": pl.Boolean,
        "DATE": pl.Date,
        "TIMESTAMP": pl.Datetime,
    }

    def __init__(
        self,
        node_id: str,
        column: Optional[str] = None,
        target_type: Optional[str] = None,
        casts: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
    ):
        d = data.copy() if data else {}
        if column is not None:
            d["column"] = column
        if target_type is not None:
            d["target_type"] = target_type
        if casts is not None:
            d["casts"] = casts
        super().__init__(node_id, d)

        c_dict = self.data.get("casts") or {}
        col = self.data.get("column")
        tt = self.data.get("target_type")
        if col and tt:
            c_dict[col] = tt

        # Also support string format "col1:int, col2:text"
        if not c_dict and self.data.get("type_mapping"):
            raw_map = str(self.data.get("type_mapping"))
            for chunk in raw_map.split(","):
                if ":" in chunk:
                    c, t = chunk.split(":", 1)
                    if c.strip() and t.strip():
                        c_dict[c.strip()] = t.strip()

        self.casts = {col_n: self.SUPPORTED_TYPES.get(t_str.lower(), "VARCHAR") for col_n, t_str in c_dict.items()}

    def validate(self) -> List[str]:
        if not self.casts:
            return [f"CastColumn node '{self.node_id}' missing column cast targets."]
        return []

    def execute(self, df: pl.DataFrame) -> pl.DataFrame:
        exprs = []
        for col_n, duck_type in self.casts.items():
            pl_type = self.POLARS_TYPES.get(duck_type, pl.Utf8)
            exprs.append(pl.col(col_n).cast(pl_type))
        return df.with_columns(exprs)

    def to_ibis_expr(self, input_expr: ir.Table) -> ir.Table:
        ibis_casts = {}
        for col_n, duck_type in self.casts.items():
            ibis_casts[col_n] = input_expr[col_n].cast(duck_type.lower())
        return input_expr.mutate(**ibis_casts)

    def to_sql_expr(self, input_table: str) -> str:
        table_expr = _format_input_table(input_table)
        cols_str = ", ".join(self.casts.keys())
        cast_exprs = ", ".join(f"CAST({c} AS {t}) AS {c}" for c, t in self.casts.items())
        return f"SELECT * EXCLUDE ({cols_str}), {cast_exprs} FROM {table_expr}"


class SplitColumnNode(BaseETLNode):
    """Split text column by delimiter transformation node."""

    def __init__(
        self,
        node_id: str,
        column: Optional[str] = None,
        delimiter: str = " ",
        new_columns: Optional[List[str] | str] = None,
        data: Optional[Dict[str, Any]] = None,
    ):
        d = data.copy() if data else {}
        if column is not None:
            d["column"] = column
        if delimiter:
            d["delimiter"] = delimiter
        if new_columns is not None:
            d["new_columns"] = new_columns
        super().__init__(node_id, d)

        self.column = self.data.get("column")
        self.delimiter = self.data.get("delimiter") if self.data.get("delimiter") is not None else " "
        new_cols = self.data.get("new_columns") or []
        if isinstance(new_cols, str):
            new_cols = [c.strip() for c in new_cols.split(",") if c.strip()]
        self.new_columns = list(new_cols or [])

    def validate(self) -> List[str]:
        if not self.column:
            return [f"SplitColumn node '{self.node_id}' missing source column."]
        if not self.new_columns:
            return [f"SplitColumn node '{self.node_id}' missing new_columns list."]
        return []

    def execute(self, df: pl.DataFrame) -> pl.DataFrame:
        split_df = df.with_columns(
            pl.col(self.column).str.split(self.delimiter).alias("_split_parts")
        )
        exprs = [
            pl.col("_split_parts").list.get(i).alias(col_name)
            for i, col_name in enumerate(self.new_columns)
        ]
        return split_df.with_columns(exprs).drop("_split_parts")

    def to_sql_expr(self, input_table: str) -> str:
        table_expr = _format_input_table(input_table)
        parts_exprs = [
            f"STR_SPLIT_PART({self.column}, '{self.delimiter}', {i + 1}) AS {col_name}"
            for i, col_name in enumerate(self.new_columns)
        ]
        return f"SELECT *, {', '.join(parts_exprs)} FROM {table_expr}"


class TextTransformNode(BaseETLNode):
    """Text formatting transformation node (Trim, Upper, Lower, Clean)."""

    def __init__(
        self,
        node_id: str,
        columns: Optional[List[str] | str] = None,
        transform_type: str = "trim",
        data: Optional[Dict[str, Any]] = None,
    ):
        d = data.copy() if data else {}
        if columns is not None:
            d["columns"] = columns
        if transform_type:
            d["transform_action"] = transform_type
        super().__init__(node_id, d)

        cols = self.data.get("columns", [])
        if isinstance(cols, str):
            cols = [c.strip() for c in cols.split(",") if c.strip()]
        self.columns = list(cols or [])
        self.transform_action = (self.data.get("transform_action") or self.data.get("action") or "trim").lower()

    def validate(self) -> List[str]:
        if not self.columns:
            return [f"TextTransform node '{self.node_id}' missing target columns."]
        return []

    def execute(self, df: pl.DataFrame) -> pl.DataFrame:
        exprs = []
        for c in self.columns:
            if self.transform_action == "trim":
                exprs.append(pl.col(c).str.strip_chars())
            elif self.transform_action in ("upper", "uppercase"):
                exprs.append(pl.col(c).str.to_uppercase())
            elif self.transform_action in ("lower", "lowercase"):
                exprs.append(pl.col(c).str.to_lowercase())
            elif self.transform_action == "clean":
                exprs.append(pl.col(c).str.replace_all(r"[^a-zA-Z0-9 ]", ""))
        return df.with_columns(exprs)

    def to_ibis_expr(self, input_expr: ir.Table) -> ir.Table:
        ibis_exprs = {}
        for c in self.columns:
            if self.transform_action == "trim":
                ibis_exprs[c] = input_expr[c].strip()
            elif self.transform_action in ("upper", "uppercase"):
                ibis_exprs[c] = input_expr[c].upper()
            elif self.transform_action in ("lower", "lowercase"):
                ibis_exprs[c] = input_expr[c].lower()
            elif self.transform_action == "clean":
                ibis_exprs[c] = input_expr[c].re_replace(r"[^a-zA-Z0-9 ]", "")
        return input_expr.mutate(**ibis_exprs)

    def to_sql_expr(self, input_table: str) -> str:
        table_expr = _format_input_table(input_table)
        cols_str = ", ".join(self.columns)
        sql_exprs = []
        for c in self.columns:
            if self.transform_action == "trim":
                sql_exprs.append(f"TRIM({c}) AS {c}")
            elif self.transform_action in ("upper", "uppercase"):
                sql_exprs.append(f"UPPER({c}) AS {c}")
            elif self.transform_action in ("lower", "lowercase"):
                sql_exprs.append(f"LOWER({c}) AS {c}")
            elif self.transform_action == "clean":
                sql_exprs.append(f"REGEXP_REPLACE({c}, '[^a-zA-Z0-9 ]', '', 'g') AS {c}")
        return f"SELECT * EXCLUDE ({cols_str}), {', '.join(sql_exprs)} FROM {table_expr}"


class DeduplicateNode(BaseETLNode):
    """Deduplicate rows transformation node."""

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
        self.columns = list(cols or [])

    def validate(self) -> List[str]:
        return []

    def execute(self, df: pl.DataFrame) -> pl.DataFrame:
        if self.columns:
            return df.unique(subset=self.columns)
        return df.unique()

    def to_ibis_expr(self, input_expr: ir.Table) -> ir.Table:
        if self.columns:
            return input_expr.distinct(on=self.columns)
        return input_expr.distinct()

    def to_sql_expr(self, input_table: str) -> str:
        table_expr = _format_input_table(input_table)
        if self.columns:
            cols_str = ", ".join(self.columns)
            return f"SELECT * FROM {table_expr} QUALIFY ROW_NUMBER() OVER (PARTITION BY {cols_str}) = 1"
        return f"SELECT DISTINCT * FROM {table_expr}"


class ConditionalColumnNode(BaseETLNode):
    """Add a conditional column (If-Then-Else CASE WHEN) transformation node."""

    def __init__(
        self,
        node_id: str,
        new_column: Optional[str] = None,
        if_condition: Optional[str] = None,
        then_value: Any = None,
        else_value: Any = None,
        cases: Optional[List[Dict[str, Any]]] = None,
        data: Optional[Dict[str, Any]] = None,
    ):
        d = data.copy() if data else {}
        if new_column is not None:
            d["new_column"] = new_column
        if if_condition is not None:
            d["if_condition"] = if_condition
        if then_value is not None:
            d["then_value"] = then_value
        if else_value is not None:
            d["else_value"] = else_value
        if cases is not None:
            d["cases"] = cases
        super().__init__(node_id, d)

        self.new_column = self.data.get("new_column") or "conditional_col"
        self.if_condition = self.data.get("if_condition") or self.data.get("condition")
        self.then_value = self.data.get("then_value") or self.data.get("then")
        self.else_value = self.data.get("else_value") if self.data.get("else_value") is not None else self.data.get("else")
        self.cases = self.data.get("cases") or []

    def validate(self) -> List[str]:
        if not self.new_column:
            return [f"ConditionalColumn node '{self.node_id}' missing new_column name."]
        if not self.if_condition and not self.cases:
            return [f"ConditionalColumn node '{self.node_id}' missing if_condition or cases."]
        return []

    def _build_case_expr(self) -> str:
        if self.cases:
            parts = []
            for item in self.cases:
                cond = item.get("when") or item.get("if_condition")
                val = item.get("then") or item.get("then_value")
                val_str = f"'{val}'" if isinstance(val, str) else str(val)
                parts.append(f"WHEN {cond} THEN {val_str}")
            else_val = self.else_value if self.else_value is not None else "NULL"
            else_str = f"'{else_val}'" if isinstance(else_val, str) else str(else_val)
            return f"CASE {' '.join(parts)} ELSE {else_str} END"

        val_str = f"'{self.then_value}'" if isinstance(self.then_value, str) else str(self.then_value)
        else_val = self.else_value if self.else_value is not None else "NULL"
        else_str = f"'{else_val}'" if isinstance(else_val, str) else str(else_val)
        return f"CASE WHEN {self.if_condition} THEN {val_str} ELSE {else_str} END"

    def execute(self, df: pl.DataFrame) -> pl.DataFrame:
        # Polars evaluation via DuckDB in-memory query for complex SQL conditions
        import duckdb
        conn = duckdb.connect()
        conn.register("source_df", df)
        try:
            case_sql = self._build_case_expr()
            res_df = conn.query(f"SELECT *, {case_sql} AS {self.new_column} FROM source_df").pl()
            return res_df
        finally:
            try:
                conn.unregister("source_df")
            except Exception:
                pass

    def to_sql_expr(self, input_table: str) -> str:
        table_expr = _format_input_table(input_table)
        case_sql = self._build_case_expr()
        return f"SELECT *, {case_sql} AS {self.new_column} FROM {table_expr}"


class IndexColumnNode(BaseETLNode):
    """Add an index (row number) column transformation node."""

    def __init__(
        self,
        node_id: str,
        column_name: str = "index",
        start_value: int = 1,
        increment: int = 1,
        data: Optional[Dict[str, Any]] = None,
    ):
        d = data.copy() if data else {}
        if column_name:
            d["column_name"] = column_name
        if start_value is not None:
            d["start_value"] = start_value
        if increment is not None:
            d["increment"] = increment
        super().__init__(node_id, d)

        self.column_name = self.data.get("column_name") or "index"
        self.start_value = int(self.data.get("start_value", 1))
        self.increment = int(self.data.get("increment", 1))

    def validate(self) -> List[str]:
        if not self.column_name:
            return [f"IndexColumn node '{self.node_id}' missing column_name."]
        return []

    def execute(self, df: pl.DataFrame) -> pl.DataFrame:
        if self.increment == 1 and self.start_value == 1:
            return df.with_row_index(name=self.column_name, offset=1)
        elif self.increment == 1 and self.start_value == 0:
            return df.with_row_index(name=self.column_name, offset=0)
        else:
            df_idx = df.with_row_index(name="_row_num", offset=0)
            return df_idx.with_columns(
                (pl.col("_row_num") * self.increment + self.start_value).alias(self.column_name)
            ).drop("_row_num")

    def to_sql_expr(self, input_table: str) -> str:
        table_expr = _format_input_table(input_table)
        if self.increment == 1 and self.start_value == 1:
            idx_expr = f"ROW_NUMBER() OVER () AS {self.column_name}"
        else:
            idx_expr = f"({self.start_value} + (ROW_NUMBER() OVER () - 1) * {self.increment}) AS {self.column_name}"
        return f"SELECT *, {idx_expr} FROM {table_expr}"


class CalculatedColumnNode(BaseETLNode):
    """Add (or replace) a calculated column built from the input data."""

    @property
    def foldable(self) -> bool:
        # The expression is plain DuckDB SQL, so materialize with Polars/DuckDB
        # and let the compiler continue from the resulting table.
        return False

    def validate(self) -> List[str]:
        errors: List[str] = []
        new_column = str(self.data.get("new_column") or "").strip()
        if not new_column:
            errors.append(f"Add Column node '{self.node_id}' missing the new column name.")
        try:
            build_calculated_expression(
                mode=self.data.get("mode") or "concat",
                columns=self.data.get("columns"),
                separator=self.data.get("separator"),
                expression=self.data.get("expression"),
                trim=bool(self.data.get("trim", True)),
            )
        except ValueError as err:
            errors.append(f"Add Column node '{self.node_id}': {err}")
        return errors

    def transform_fn(self, df: pl.DataFrame) -> pl.DataFrame:
        return apply_calculated_column(
            df,
            new_column=self.data.get("new_column") or "",
            mode=self.data.get("mode") or "concat",
            columns=self.data.get("columns"),
            separator=self.data.get("separator"),
            expression=self.data.get("expression"),
            trim=bool(self.data.get("trim", True)),
        )

    def to_sql_expr(self, input_table: str) -> str:
        expr = build_calculated_expression(
            mode=self.data.get("mode") or "concat",
            columns=self.data.get("columns"),
            separator=self.data.get("separator"),
            expression=self.data.get("expression"),
            trim=bool(self.data.get("trim", True)),
        )
        target = quote_identifier(self.data.get("new_column") or "new_column")
        table_expr = _format_input_table(input_table)
        return f"SELECT *, {expr} AS {target} FROM {table_expr}"
