"""DAX-to-SQL Translator Engine for PyBI Semantic Model."""

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

        def decorator(func: Callable[[List[str], Optional[Any]], str]):
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
        """Fallback identifier resolution for simple aggregation keywords and identifiers."""
        resolved = expr
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
        return f"COUNT({arg})"
    return "COUNT(*)"


@DaxEngine.register("CALCULATE")
def _translate_calculate(args: List[str], model: Optional[Any] = None) -> str:
    if not args or not args[0]:
        return "NULL"
    # First argument is expression. Additional arguments are filters resolved by query resolver.
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


@DaxEngine.register("FILTER")
def _translate_filter(args: List[str], model: Optional[Any] = None) -> str:
    if len(args) < 2:
        raise ValueError("FILTER requires 2 arguments: table and filter condition")
    cond = DaxEngine.translate(args[1], model)
    return f"({cond})"


@DaxEngine.register("TOTALYTD")
def _translate_totalytd(args: List[str], model: Optional[Any] = None) -> str:
    if len(args) < 2:
        raise ValueError("TOTALYTD requires 2 arguments: expression and date column")
    expr = DaxEngine.translate(args[0], model)
    date_col = DaxEngine.translate(args[1], model)
    if any(expr.upper().startswith(agg) for agg in ("SUM(", "AVG(", "COUNT(", "MIN(", "MAX(")):
        return f"{expr} OVER (PARTITION BY YEAR({date_col}) ORDER BY {date_col})"
    return f"SUM({expr}) OVER (PARTITION BY YEAR({date_col}) ORDER BY {date_col})"
