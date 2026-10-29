"""Polars Code Generator & Transpiler for native Python ETL operations in PyBI."""

from typing import Any, Dict, List, Optional, Union
import polars as pl

from pybi.schemas.etl import ETLQuery, ETLStep


class PolarsCodeGenerator:
    """
    Transpiles JSON sequences of transformations (ETLQuery / ETLStep) into native Polars Python code,
    and executes the pipeline natively using Polars.
    """

    def __init__(self, query: Union[ETLQuery, Dict[str, Any]]):
        if hasattr(query, "model_dump"):
            self.query_dict = query.model_dump()
            self.query_obj = query
        elif isinstance(query, dict):
            self.query_dict = query
            self.query_obj = ETLQuery.model_validate(query) if query else ETLQuery()
        else:
            self.query_dict = {}
            self.query_obj = ETLQuery()

        self.query_id = (
            self.query_dict.get("query_id")
            or self.query_dict.get("query_name")
            or getattr(self.query_obj, "query_name", "query_1")
        )

        source_info = self.query_dict.get("source") or {}
        self.source_type = (
            self.query_dict.get("source_type")
            or source_info.get("type")
            or source_info.get("source_type")
            or "csv"
        ).lower()

        self.source_path = (
            self.query_dict.get("source_path_or_conn")
            or source_info.get("path")
            or source_info.get("file_path")
            or source_info.get("filepath")
            or source_info.get("table_name")
            or source_info.get("table")
            or "data.csv"
        )

        raw_steps = self.query_dict.get("steps") or getattr(self.query_obj, "steps", [])
        self.steps: List[ETLStep] = []
        for s in raw_steps:
            if isinstance(s, ETLStep):
                self.steps.append(s)
            elif isinstance(s, dict):
                self.steps.append(ETLStep.model_validate(s))

    def generate_python_code(self) -> str:
        """
        Generates formatted standalone Python script using Polars.
        """
        code_lines = [
            "# Script generato automaticamente da PYBI ETL Engine",
            "import polars as pl",
            "",
            "def run_pipeline():",
        ]

        # Step 1: Caricamento Sorgente
        if self.source_type in ("csv", "text"):
            code_lines.append(f'    df = pl.read_csv("{self.source_path}")')
        elif self.source_type == "parquet":
            code_lines.append(f'    df = pl.read_parquet("{self.source_path}")')
        elif self.source_type == "excel":
            code_lines.append(f'    df = pl.read_excel("{self.source_path}")')
        elif self.source_type == "json":
            code_lines.append(f'    df = pl.read_json("{self.source_path}")')
        else:
            code_lines.append(f'    # Sorgente custom: {self.source_path}')
            code_lines.append('    df = pl.DataFrame()')

        # Step 2: Applicazione sequenziale dei passaggi
        for step in self.steps:
            step_code = self._transpile_step_to_polars(step)
            if step_code:
                code_lines.append(f"    # Step: {step.name}")
                code_lines.append(f"    df = {step_code}")

        code_lines.append("")
        code_lines.append("    return df")
        code_lines.append("")
        code_lines.append('if __name__ == "__main__":')
        code_lines.append("    result_df = run_pipeline()")
        code_lines.append("    print(result_df.head(10))")

        return "\n".join(code_lines)

    def _transpile_step_to_polars(self, step: ETLStep) -> str:
        """
        Maps a single ETLStep to Polars Python code.
        """
        stype = step.step_type.lower() if step.step_type else ""
        params = step.params or {}

        if stype in ("filter", "filter_rows"):
            col = params.get("column")
            op = str(params.get("operator", "==")).lower().strip()
            val = params.get("value")

            if col and val is not None:
                if isinstance(val, str):
                    formatted_val = f'"{val}"'
                else:
                    formatted_val = str(val)

                if op in ("==", "equals", "="):
                    return f'df.filter(pl.col("{col}") == {formatted_val})'
                elif op in (">=", "greater_than_or_equal"):
                    return f'df.filter(pl.col("{col}") >= {formatted_val})'
                elif op in ("<=", "less_than_or_equal"):
                    return f'df.filter(pl.col("{col}") <= {formatted_val})'
                elif op in ("!=", "not_equals", "<>"):
                    return f'df.filter(pl.col("{col}") != {formatted_val})'
                elif op in (">", "greater_than"):
                    return f'df.filter(pl.col("{col}") > {formatted_val})'
                elif op in ("<", "less_than"):
                    return f'df.filter(pl.col("{col}") < {formatted_val})'
                elif op in ("contains", "string_contains"):
                    clean_val = val if isinstance(val, str) else str(val)
                    return f'df.filter(pl.col("{col}").str.contains("{clean_val}"))'

        elif stype in ("cast", "cast_column", "change_type"):
            col = params.get("column")
            target_type = params.get("to_type") or params.get("target_type") or params.get("new_type")
            casts = params.get("casts") or {}
            if not casts and col and target_type:
                casts = {col: target_type}

            if casts:
                type_map = {
                    "float": "Float64", "float64": "Float64", "double": "Float64",
                    "int": "Int64", "int64": "Int64", "integer": "Int64", "bigint": "Int64",
                    "str": "Utf8", "string": "Utf8", "utf8": "Utf8", "text": "Utf8", "varchar": "Utf8",
                    "bool": "Boolean", "boolean": "Boolean",
                    "date": "Date", "datetime": "Datetime", "timestamp": "Datetime",
                }
                cast_exprs = []
                for c, t in casts.items():
                    pl_t = type_map.get(str(t).lower(), str(t))
                    cast_exprs.append(f'pl.col("{c}").cast(pl.{pl_t})')
                return f'df.with_columns([{", ".join(cast_exprs)}])'

        elif stype in ("rename", "rename_column"):
            mapping = params.get("mapping") or {}
            old_col = params.get("old_name") or params.get("old_column")
            new_col = params.get("new_name") or params.get("new_column")
            if not mapping and old_col and new_col:
                mapping = {old_col: new_col}
            if mapping:
                return f'df.rename({mapping})'

        elif stype in ("remove_columns", "remove_column", "drop_column"):
            cols = params.get("columns") or params.get("column")
            if isinstance(cols, str):
                cols = [cols]
            if cols:
                return f'df.drop({cols})'

        elif stype in ("add_column", "calculated_column", "custom_column", "add_custom_column"):
            col_name = params.get("new_column") or params.get("column_name") or params.get("column") or "custom_col"
            expr_type = params.get("expr_type") or ("concat" if "concat_columns" in params or "columns" in params else "expression")

            if expr_type == "concat" or "concat_columns" in params:
                cols_to_concat = params.get("concat_columns") or params.get("columns") or []
                sep = params.get("separator", " ")
                if isinstance(cols_to_concat, str):
                    cols_to_concat = [c.strip() for c in cols_to_concat.split(",") if c.strip()]
                cols_str = ", ".join([f'pl.col("{c}")' for c in cols_to_concat])
                return f'df.with_columns(pl.concat_str([{cols_str}], separator="{sep}").alias("{col_name}"))'

            elif expr_type == "conditional" or "cond_col" in params or "if_condition" in params:
                cond_col = params.get("cond_col") or params.get("if_condition") or "col"
                cond_op = params.get("cond_op", "==")
                cond_val = params.get("cond_val") if params.get("cond_val") is not None else params.get("value")
                val_true = params.get("val_true") if params.get("val_true") is not None else params.get("then_value")
                val_false = params.get("val_false") if params.get("val_false") is not None else params.get("else_value")

                formatted_cond_val = f'"{cond_val}"' if isinstance(cond_val, str) else str(cond_val)
                formatted_true = f'"{val_true}"' if isinstance(val_true, str) else str(val_true)
                formatted_false = f'"{val_false}"' if isinstance(val_false, str) else str(val_false)

                return (
                    f'df.with_columns(pl.when(pl.col("{cond_col}") {cond_op} {formatted_cond_val})'
                    f'.then(pl.lit({formatted_true}))'
                    f'.otherwise(pl.lit({formatted_false})).alias("{col_name}"))'
                )

            elif params.get("expression"):
                expr = params.get("expression")
                return f'df.with_columns(({expr}).alias("{col_name}"))'

        elif stype in ("group_by", "groupby"):
            by_cols = (
                params.get("group_columns")
                or params.get("group_by_columns")
                or params.get("group_by")
                or params.get("by")
                or params.get("columns")
            )
            if isinstance(by_cols, str):
                by_cols = [by_cols]
            aggregations = params.get("aggregations") or []

            aggs_str = []
            if isinstance(aggregations, list):
                for a in aggregations:
                    c = a.get("col") or a.get("column")
                    agg_fn = str(a.get("agg") or a.get("function") or "sum").lower()
                    alias = a.get("alias") or f"{c}_{agg_fn}"
                    aggs_str.append(f'pl.col("{c}").{agg_fn}().alias("{alias}")')
            elif isinstance(aggregations, dict):
                for c, agg_fn in aggregations.items():
                    fn = str(agg_fn).lower()
                    aggs_str.append(f'pl.col("{c}").{fn}().alias("{c}_{fn}")')

            aggs_joined = ", ".join(aggs_str)
            return f'df.group_by({by_cols}).agg([{aggs_joined}])'

        elif stype in ("sort", "sort_rows", "order_by"):
            by_col = params.get("column") or params.get("by") or params.get("columns")
            descending = params.get("descending", False)
            if isinstance(by_col, list) and len(by_col) == 1:
                by_col = by_col[0]
            if isinstance(by_col, list):
                return f'df.sort({by_col}, descending={descending})'
            elif by_col:
                return f'df.sort("{by_col}", descending={descending})'

        elif stype in ("join", "merge"):
            other_var = params.get("target_table") or params.get("right_table") or "other_df"
            left_on = params.get("left_on") or params.get("source_column") or params.get("on")
            right_on = params.get("right_on") or params.get("target_column") or params.get("on")
            how = str(params.get("how") or params.get("join_type") or "left").lower()

            if left_on and right_on and left_on != right_on:
                return f'df.join({other_var}, left_on="{left_on}", right_on="{right_on}", how="{how}")'
            elif left_on:
                return f'df.join({other_var}, on="{left_on}", how="{how}")'

        elif stype in ("deduplicate", "distinct", "remove_duplicates"):
            cols = params.get("columns")
            if isinstance(cols, str):
                cols = [cols]
            if cols:
                return f'df.unique(subset={cols})'
            return 'df.unique()'

        elif stype in ("replace", "replace_values"):
            col = params.get("column")
            old_val = params.get("old_value")
            new_val = params.get("new_value")
            if col and old_val is not None and new_val is not None:
                fmt_old = f'"{old_val}"' if isinstance(old_val, str) else str(old_val)
                fmt_new = f'"{new_val}"' if isinstance(new_val, str) else str(new_val)
                return f'df.with_columns(pl.col("{col}").replace({fmt_old}, {fmt_new}))'

        elif stype in ("text_transform", "format"):
            cols = params.get("columns") or params.get("column")
            action = str(params.get("action") or params.get("transform_action") or "trim").lower()
            if isinstance(cols, str):
                cols = [cols]
            if cols:
                exprs = []
                for c in cols:
                    if action in ("trim", "strip"):
                        exprs.append(f'pl.col("{c}").str.strip_chars()')
                    elif action in ("upper", "uppercase"):
                        exprs.append(f'pl.col("{c}").str.to_uppercase()')
                    elif action in ("lower", "lowercase"):
                        exprs.append(f'pl.col("{c}").str.to_lowercase()')
                if exprs:
                    return f'df.with_columns([{", ".join(exprs)}])'

        return ""

    def execute_pipeline(self, initial_df: Optional[pl.DataFrame] = None) -> pl.DataFrame:
        """
        Executes the ETL transformations natively using Polars DataFrame operations.
        """
        if initial_df is not None:
            df = initial_df.clone()
        else:
            if self.source_type in ("csv", "text"):
                df = pl.read_csv(self.source_path)
            elif self.source_type == "parquet":
                df = pl.read_parquet(self.source_path)
            elif self.source_type == "excel":
                df = pl.read_excel(self.source_path)
            elif self.source_type == "json":
                df = pl.read_json(self.source_path)
            else:
                df = pl.DataFrame()

        for step in self.steps:
            stype = step.step_type.lower() if step.step_type else ""
            params = step.params or {}

            if stype in ("filter", "filter_rows"):
                col = params.get("column")
                op = str(params.get("operator", "==")).lower().strip()
                val = params.get("value")
                if col in df.columns and val is not None:
                    if op in ("==", "equals", "="):
                        df = df.filter(pl.col(col) == val)
                    elif op in (">=", "greater_than_or_equal"):
                        df = df.filter(pl.col(col) >= val)
                    elif op in ("<=", "less_than_or_equal"):
                        df = df.filter(pl.col(col) <= val)
                    elif op in ("!=", "not_equals", "<>"):
                        df = df.filter(pl.col(col) != val)
                    elif op in (">", "greater_than"):
                        df = df.filter(pl.col(col) > val)
                    elif op in ("<", "less_than"):
                        df = df.filter(pl.col(col) < val)
                    elif op in ("contains", "string_contains"):
                        df = df.filter(pl.col(col).str.contains(str(val)))

            elif stype in ("cast", "cast_column", "change_type"):
                col = params.get("column")
                target_type = params.get("to_type") or params.get("target_type") or params.get("new_type")
                casts = params.get("casts") or {}
                if not casts and col and target_type:
                    casts = {col: target_type}

                type_map = {
                    "float": pl.Float64, "float64": pl.Float64, "double": pl.Float64,
                    "int": pl.Int64, "int64": pl.Int64, "integer": pl.Int64, "bigint": pl.Int64,
                    "str": pl.Utf8, "string": pl.Utf8, "utf8": pl.Utf8, "text": pl.Utf8,
                    "bool": pl.Boolean, "boolean": pl.Boolean,
                    "date": pl.Date, "datetime": pl.Datetime,
                }
                for c, t in casts.items():
                    if c in df.columns:
                        pl_t = type_map.get(str(t).lower(), pl.Utf8)
                        df = df.with_columns(pl.col(c).cast(pl_t))

            elif stype in ("rename", "rename_column"):
                mapping = params.get("mapping") or {}
                old_col = params.get("old_name") or params.get("old_column")
                new_col = params.get("new_name") or params.get("new_column")
                if not mapping and old_col and new_col:
                    mapping = {old_col: new_col}
                valid_mapping = {k: v for k, v in mapping.items() if k in df.columns}
                if valid_mapping:
                    df = df.rename(valid_mapping)

            elif stype in ("remove_columns", "remove_column", "drop_column"):
                cols = params.get("columns") or params.get("column")
                if isinstance(cols, str):
                    cols = [cols]
                if cols:
                    exist_cols = [c for c in cols if c in df.columns]
                    if exist_cols:
                        df = df.drop(exist_cols)

            elif stype in ("add_column", "calculated_column", "custom_column", "add_custom_column"):
                col_name = params.get("new_column") or params.get("column_name") or params.get("column") or "custom_col"
                expr_type = params.get("expr_type") or ("concat" if "concat_columns" in params or "columns" in params else "expression")

                if expr_type == "concat" or "concat_columns" in params:
                    cols_to_concat = params.get("concat_columns") or params.get("columns") or []
                    sep = params.get("separator", " ")
                    if isinstance(cols_to_concat, str):
                        cols_to_concat = [c.strip() for c in cols_to_concat.split(",") if c.strip()]
                    exist_concat = [c for c in cols_to_concat if c in df.columns]
                    if exist_concat:
                        df = df.with_columns(pl.concat_str([pl.col(c) for c in exist_concat], separator=sep).alias(col_name))

                elif expr_type == "conditional" or "cond_col" in params or "if_condition" in params:
                    cond_col = params.get("cond_col") or params.get("if_condition") or "col"
                    cond_op = params.get("cond_op", "==")
                    cond_val = params.get("cond_val") if params.get("cond_val") is not None else params.get("value")
                    val_true = params.get("val_true") if params.get("val_true") is not None else params.get("then_value")
                    val_false = params.get("val_false") if params.get("val_false") is not None else params.get("else_value")

                    if cond_col in df.columns:
                        if cond_op in ("==", "="):
                            cond_expr = pl.col(cond_col) == cond_val
                        elif cond_op in (">=",):
                            cond_expr = pl.col(cond_col) >= cond_val
                        elif cond_op in ("<=",):
                            cond_expr = pl.col(cond_col) <= cond_val
                        elif cond_op in ("!=",):
                            cond_expr = pl.col(cond_col) != cond_val
                        elif cond_op in (">",):
                            cond_expr = pl.col(cond_col) > cond_val
                        elif cond_op in ("<",):
                            cond_expr = pl.col(cond_col) < cond_val
                        else:
                            cond_expr = pl.col(cond_col) == cond_val

                        df = df.with_columns(
                            pl.when(cond_expr).then(pl.lit(val_true)).otherwise(pl.lit(val_false)).alias(col_name)
                        )

            elif stype in ("group_by", "groupby"):
                by_cols = (
                    params.get("group_columns")
                    or params.get("group_by_columns")
                    or params.get("group_by")
                    or params.get("by")
                    or params.get("columns")
                )
                if isinstance(by_cols, str):
                    by_cols = [by_cols]
                by_cols = [c for c in by_cols if c in df.columns] if by_cols else []
                aggregations = params.get("aggregations") or []

                aggs = []
                if isinstance(aggregations, list):
                    for a in aggregations:
                        c = a.get("col") or a.get("column")
                        agg_fn = str(a.get("agg") or a.get("function") or "sum").lower()
                        alias = a.get("alias") or f"{c}_{agg_fn}"
                        if c in df.columns:
                            aggs.append(getattr(pl.col(c), agg_fn)().alias(alias))
                elif isinstance(aggregations, dict):
                    for c, agg_fn in aggregations.items():
                        fn = str(agg_fn).lower()
                        if c in df.columns:
                            aggs.append(getattr(pl.col(c), fn)().alias(f"{c}_{fn}"))

                if by_cols:
                    df = df.group_by(by_cols).agg(aggs)

            elif stype in ("sort", "sort_rows", "order_by"):
                by_col = params.get("column") or params.get("by") or params.get("columns")
                descending = params.get("descending", False)
                if isinstance(by_col, list):
                    valid_by = [c for c in by_col if c in df.columns]
                    if valid_by:
                        df = df.sort(valid_by, descending=descending)
                elif isinstance(by_col, str) and by_col in df.columns:
                    df = df.sort(by_col, descending=descending)

            elif stype in ("deduplicate", "distinct", "remove_duplicates"):
                cols = params.get("columns")
                if isinstance(cols, str):
                    cols = [cols]
                if cols:
                    exist_cols = [c for c in cols if c in df.columns]
                    if exist_cols:
                        df = df.unique(subset=exist_cols)
                else:
                    df = df.unique()

            elif stype in ("replace", "replace_values"):
                col = params.get("column")
                old_val = params.get("old_value")
                new_val = params.get("new_value")
                if col in df.columns and old_val is not None and new_val is not None:
                    df = df.with_columns(pl.col(col).replace(old_val, new_val))

            elif stype in ("text_transform", "format"):
                cols = params.get("columns") or params.get("column")
                action = str(params.get("action") or params.get("transform_action") or "trim").lower()
                if isinstance(cols, str):
                    cols = [cols]
                if cols:
                    for c in cols:
                        if c in df.columns:
                            if action in ("trim", "strip"):
                                df = df.with_columns(pl.col(c).str.strip_chars())
                            elif action in ("upper", "uppercase"):
                                df = df.with_columns(pl.col(c).str.to_uppercase())
                            elif action in ("lower", "lowercase"):
                                df = df.with_columns(pl.col(c).str.to_lowercase())

        return df
