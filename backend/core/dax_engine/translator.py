"""DAX-to-SQL Translator Engine for PyBI Semantic Model."""

import inspect
import re
from typing import Any, Callable, Dict, List, Optional
from backend.core.interfaces import IDaxTranslator


class DaxEngine(IDaxTranslator):
    """
    AST-like DAX-to-SQL translator engine using an extensible decorator registry pattern.
    Translates DAX functions into valid DuckDB SQL query fragments.
    """

    _registry: Dict[str, Callable[[List[str], Optional[Any]], str]] = {}

    @classmethod
    def register(cls, func_name: str):
        """Decorator to register a DAX function translator into the DaxEngine."""

        def decorator(func: Callable):
            sig = inspect.signature(func)
            params = len(sig.parameters)

            if params == 1:
                def wrapped(args: List[str], model: Optional[Any] = None) -> str:
                    return func(args)

                cls._registry[func_name.upper()] = wrapped
            else:
                cls._registry[func_name.upper()] = func

            return func

        return decorator

    @classmethod
    def translate(cls, expression: str, model: Optional[Any] = None) -> str:
        """Translate a DAX expression string into a DuckDB SQL fragment."""
        if not expression or not expression.strip():
            return ""

        expr = re.sub(r"\s+", " ", expression).strip()

        # Match top-level function call: FUNC_NAME(arg1, arg2, ...)
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*\((.*)\)$", expr, re.DOTALL)

        if match:
            func_name = match.group(1).upper()
            if func_name in cls._registry:
                args = cls._parse_args(match.group(2))
                return cls._registry[func_name](args, model)

        # Fallback for expressions or direct column/measure replacements
        return cls._resolve_identifiers(expr, model)

    @classmethod
    def _parse_args(cls, args_str: str) -> List[str]:
        """Parses function arguments by comma, respecting nested parentheses and quotes."""
        args: List[str] = []
        current: List[str] = []
        depth = 0
        in_single_quote = False
        in_double_quote = False

        for char in args_str:
            if char == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
                current.append(char)
            elif char == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
                current.append(char)
            elif not in_single_quote and not in_double_quote:
                if char == "(":
                    depth += 1
                    current.append(char)
                elif char == ")":
                    depth -= 1
                    current.append(char)
                elif char == "," and depth == 0:
                    args.append("".join(current).strip())
                    current = []
                else:
                    current.append(char)
            else:
                current.append(char)

        if current or not args_str:
            arg_text = "".join(current).strip()
            if arg_text:
                args.append(arg_text)

        return args

    @classmethod
    def _resolve_identifiers(cls, expr: str, model: Optional[Any] = None) -> str:
        """Fallback identifier resolution for DAX syntax, column/table references, and operators."""
        if not expr:
            return ""

        resolved = expr.strip()

        # 1. String literal double quotes in DAX -> single quotes in SQL: "text" -> 'text'
        resolved = re.sub(r'"([^"\n]+)"', r"'\1'", resolved)

        # 2. Table and Column Identifiers:
        # 'Table'[Column] -> "Table"."Column"
        resolved = re.sub(r"'([A-Za-z0-9_ ]+)'\[([A-Za-z0-9_ ]+)\]", r'"\1"."\2"', resolved)
        # Table[Column] -> "Table"."Column"
        resolved = re.sub(r"([A-Za-z0-9_]+)\[([A-Za-z0-9_ ]+)\]", r'"\1"."\2"', resolved)
        # Standalone [Column] -> "Column"
        resolved = re.sub(r"(?<![\"A-Za-z0-9_\.])\[([A-Za-z0-9_ ]+)\]", r'"\1"', resolved)

        # 3. DAX Logical & Concatenation Operators:
        # && -> AND
        resolved = re.sub(r"\s*&&\s*", " AND ", resolved)
        # || -> OR
        resolved = re.sub(r"\s*\|\|\s*", " OR ", resolved)
        # Single & (string concatenation) -> ||
        resolved = re.sub(r"(?<!&)\s*&\s*(?!&)", " || ", resolved)

        # 4. Keyword fallbacks
        resolved = re.sub(r"\bAVERAGE\b", "AVG", resolved, flags=re.IGNORECASE)
        resolved = re.sub(r"\bCOUNTROWS\b", "COUNT", resolved, flags=re.IGNORECASE)

        return resolved


# Instantiated translator instance for protocol usage
dax_engine_translator = DaxEngine()


# --- Registered Function Translators ---


@DaxEngine.register("DIVIDE")
def _translate_divide(args: List[str], model: Optional[Any] = None) -> str:
    if len(args) < 2:
        raise ValueError("DIVIDE requires at least 2 arguments: numerator and denominator")
    num = DaxEngine.translate(args[0], model)
    den = DaxEngine.translate(args[1], model)
    alt = DaxEngine.translate(args[2], model) if len(args) > 2 else "0"
    return f"COALESCE({num} / NULLIF({den}, 0), {alt})"


@DaxEngine.register("IF")
def _translate_if(args: List[str], model: Optional[Any] = None) -> str:
    if len(args) < 2:
        raise ValueError("IF requires at least 2 arguments: condition and true_value")
    cond = DaxEngine.translate(args[0], model)
    true_val = DaxEngine.translate(args[1], model)
    false_val = DaxEngine.translate(args[2], model) if len(args) > 2 else "NULL"
    return f"CASE WHEN {cond} THEN {true_val} ELSE {false_val} END"


@DaxEngine.register("SUM")
def _translate_sum(args: List[str], model: Optional[Any] = None) -> str:
    if not args or not args[0]:
        raise ValueError("SUM requires 1 argument")
    arg = DaxEngine.translate(args[0], model)
    return f"SUM({arg})"


@DaxEngine.register("MIN")
def _translate_min(args: List[str], model: Optional[Any] = None) -> str:
    if not args or not args[0]:
        raise ValueError("MIN requires 1 argument")
    arg = DaxEngine.translate(args[0], model)
    return f"MIN({arg})"


@DaxEngine.register("MAX")
def _translate_max(args: List[str], model: Optional[Any] = None) -> str:
    if not args or not args[0]:
        raise ValueError("MAX requires 1 argument")
    arg = DaxEngine.translate(args[0], model)
    return f"MAX({arg})"


@DaxEngine.register("DISTINCTCOUNT")
def _translate_distinctcount(args: List[str], model: Optional[Any] = None) -> str:
    if not args or not args[0]:
        raise ValueError("DISTINCTCOUNT requires 1 argument")
    arg = DaxEngine.translate(args[0], model)
    return f"COUNT(DISTINCT {arg})"


@DaxEngine.register("COUNTA")
def _translate_counta(args: List[str], model: Optional[Any] = None) -> str:
    if not args or not args[0]:
        raise ValueError("COUNTA requires 1 argument")
    arg = DaxEngine.translate(args[0], model)
    return f"COUNT({arg})"


@DaxEngine.register("AVERAGE")
def _translate_average(args: List[str], model: Optional[Any] = None) -> str:
    if not args or not args[0]:
        raise ValueError("AVERAGE requires 1 argument")
    arg = DaxEngine.translate(args[0], model)
    return f"AVG({arg})"


@DaxEngine.register("COUNTROWS")
def _translate_countrows(args: List[str], model: Optional[Any] = None) -> str:
    if args and args[0]:
        arg = DaxEngine.translate(args[0], model)
        if arg.startswith("'") and arg.endswith("'"):
            arg = f'"{arg[1:-1]}"'
        return f"COUNT({arg})"
    return "COUNT(*)"


@DaxEngine.register("CALCULATE")
def _translate_calculate(args: List[str], model: Optional[Any] = None) -> str:
    if not args or not args[0]:
        return "NULL"
    # First argument is expression. Additional arguments are filter context modifiers.
    # TODO: Integrate with FilterContext modifier
    return DaxEngine.translate(args[0], model)


@DaxEngine.register("RELATED")
def _translate_related(args: List[str], model: Optional[Any] = None) -> str:
    if not args or not args[0]:
        return ""
    return DaxEngine.translate(args[0], model)


@DaxEngine.register("SUMX")
def _translate_sumx(args: List[str], model: Optional[Any] = None) -> str:
    if len(args) < 2:
        raise ValueError("SUMX requires 2 arguments: table and expression")
    expr = DaxEngine.translate(args[1], model)
    return f"SUM({expr})"


@DaxEngine.register("AVERAGEX")
def _translate_averagex(args: List[str], model: Optional[Any] = None) -> str:
    if len(args) < 2:
        raise ValueError("AVERAGEX requires 2 arguments: table and expression")
    expr = DaxEngine.translate(args[1], model)
    return f"AVG({expr})"


@DaxEngine.register("FILTER")
def _translate_filter(args: List[str], model: Optional[Any] = None) -> str:
    if len(args) < 2:
        raise ValueError("FILTER requires 2 arguments: table and filter condition")
    cond = DaxEngine.translate(args[1], model)
    return f"({cond})"


@DaxEngine.register("ALL")
def _translate_all(args: List[str], model: Optional[Any] = None) -> str:
    # Filter context modifier: removes active filters on table or column.
    return "1=1"


@DaxEngine.register("REMOVEFILTERS")
def _translate_removefilters(args: List[str], model: Optional[Any] = None) -> str:
    # Modern synonym for ALL as a filter modifier.
    return "1=1"


@DaxEngine.register("VALUES")
def _translate_values(args: List[str], model: Optional[Any] = None) -> str:
    if not args or not args[0]:
        raise ValueError("VALUES requires 1 argument")
    arg = DaxEngine.translate(args[0], model)
    if "." in arg:
        tbl = arg.split(".")[0]
        return f"SELECT DISTINCT {arg} FROM {tbl}"
    return f"DISTINCT {arg}"


@DaxEngine.register("SWITCH")
def _translate_switch(args: List[str], model: Optional[Any] = None) -> str:
    if len(args) < 3:
        raise ValueError("SWITCH requires at least 3 arguments")

    first_arg_str = args[0].strip().upper()
    is_true_switch = first_arg_str in ("TRUE()", "TRUE", "1")

    expr = DaxEngine.translate(args[0], model)

    remaining = args[1:]
    has_else = (len(remaining) % 2 == 1)
    pairs_count = (len(remaining) - 1) if has_else else len(remaining)

    when_clauses = []
    for i in range(0, pairs_count, 2):
        val = DaxEngine.translate(remaining[i], model)
        res = DaxEngine.translate(remaining[i + 1], model)
        if is_true_switch:
            when_clauses.append(f"WHEN {val} THEN {res}")
        else:
            when_clauses.append(f"WHEN {expr} = {val} THEN {res}")

    else_val = DaxEngine.translate(remaining[-1], model) if has_else else "NULL"
    when_str = " ".join(when_clauses)
    return f"CASE {when_str} ELSE {else_val} END"


@DaxEngine.register("ISBLANK")
def _translate_isblank(args: List[str], model: Optional[Any] = None) -> str:
    if not args or not args[0]:
        raise ValueError("ISBLANK requires 1 argument")
    arg = DaxEngine.translate(args[0], model)
    return f"({arg} IS NULL)"


@DaxEngine.register("COALESCE")
def _translate_coalesce(args: List[str], model: Optional[Any] = None) -> str:
    if not args:
        raise ValueError("COALESCE requires at least 1 argument")
    translated_args = [DaxEngine.translate(arg, model) for arg in args]
    return f"COALESCE({', '.join(translated_args)})"


@DaxEngine.register("CONCATENATE")
def _translate_concatenate(args: List[str], model: Optional[Any] = None) -> str:
    if len(args) < 2:
        raise ValueError("CONCATENATE requires at least 2 arguments")
    arg1 = DaxEngine.translate(args[0], model)
    arg2 = DaxEngine.translate(args[1], model)
    return f"CONCAT({arg1}, {arg2})"


@DaxEngine.register("UPPER")
def _translate_upper(args: List[str], model: Optional[Any] = None) -> str:
    if not args or not args[0]:
        raise ValueError("UPPER requires 1 argument")
    arg = DaxEngine.translate(args[0], model)
    return f"UPPER({arg})"


@DaxEngine.register("LOWER")
def _translate_lower(args: List[str], model: Optional[Any] = None) -> str:
    if not args or not args[0]:
        raise ValueError("LOWER requires 1 argument")
    arg = DaxEngine.translate(args[0], model)
    return f"LOWER({arg})"


@DaxEngine.register("ROUND")
def _translate_round(args: List[str], model: Optional[Any] = None) -> str:
    if len(args) < 2:
        raise ValueError("ROUND requires 2 arguments: number and digits")
    num = DaxEngine.translate(args[0], model)
    digits = DaxEngine.translate(args[1], model)
    return f"ROUND({num}, {digits})"


@DaxEngine.register("TOTALYTD")
def _translate_totalytd(args: List[str], model: Optional[Any] = None) -> str:
    if len(args) < 2:
        raise ValueError("TOTALYTD requires 2 arguments: expression and date column")
    expr = DaxEngine.translate(args[0], model)
    date_col = DaxEngine.translate(args[1], model)
    if any(expr.upper().startswith(agg) for agg in ("SUM(", "AVG(", "COUNT(", "MIN(", "MAX(")):
        return f"{expr} OVER (PARTITION BY YEAR({date_col}) ORDER BY {date_col})"
    return f"SUM({expr}) OVER (PARTITION BY YEAR({date_col}) ORDER BY {date_col})"


@DaxEngine.register("SAMEPERIODLASTYEAR")
def _translate_sameperiodlastyear(args: List[str], model: Optional[Any] = None) -> str:
    if not args or not args[0]:
        raise ValueError("SAMEPERIODLASTYEAR requires 1 argument: date column")
    date_col = DaxEngine.translate(args[0], model)
    return f"({date_col} - INTERVAL '1 year')"


@DaxEngine.register("DATEADD")
def _translate_dateadd(args: List[str], model: Optional[Any] = None) -> str:
    if len(args) < 3:
        raise ValueError("DATEADD requires 3 arguments: dates, number_of_intervals, interval")
    dates = DaxEngine.translate(args[0], model)
    num = args[1].strip()
    interval = args[2].strip().strip("'\"").lower()
    return f"({dates} + INTERVAL {num} {interval})"
