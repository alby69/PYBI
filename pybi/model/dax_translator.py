"""DAX expression translator for PyBI Semantic Model."""

import re
from typing import Callable, Dict, List


class DaxTranslator:
    """
    Translates DAX-like expressions into DuckDB SQL query fragments.
    Designed with KISS and DRY principles: extensible via a function registry.
    """

    _registry: Dict[str, Callable[[List[str]], str]] = {}

    @classmethod
    def register_function(cls, dax_func: str):
        """Decorator to register a DAX function translator."""

        def decorator(func: Callable[[List[str]], str]):
            cls._registry[dax_func.upper()] = func
            return func

        return decorator

    @classmethod
    def translate(cls, expression: str) -> str:
        """Translate a DAX-like expression into DuckDB SQL fragment."""
        if not expression:
            return ""

        expr = re.sub(r"\s+", " ", expression).strip()
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*\((.*)\)$", expr, re.DOTALL)

        if match:
            func_name = match.group(1).upper()
            if func_name in cls._registry:
                args = cls._parse_args(match.group(2))
                return cls._registry[func_name](args)

        # Fallback for simple functions or expressions not top-level in registry
        expr = re.sub(r"\bAVERAGE\b", "AVG", expr, flags=re.IGNORECASE)
        expr = re.sub(r"\bCOUNTROWS\b", "COUNT", expr, flags=re.IGNORECASE)
        return expr

    @staticmethod
    def _parse_args(args_str: str) -> List[str]:
        """Splits arguments by comma, respecting nested parentheses and quotes."""
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


# --- Registered Function Translators ---


@DaxTranslator.register_function("DIVIDE")
def _translate_divide(args: List[str]) -> str:
    if len(args) < 2:
        raise ValueError("DIVIDE requires at least 2 arguments")
    num = DaxTranslator.translate(args[0])
    den = DaxTranslator.translate(args[1])
    alt = DaxTranslator.translate(args[2]) if len(args) > 2 else "0"
    return f"COALESCE({num} / NULLIF({den}, 0), {alt})"


@DaxTranslator.register_function("IF")
def _translate_if(args: List[str]) -> str:
    if len(args) < 2:
        raise ValueError("IF requires at least 2 arguments")
    cond = DaxTranslator.translate(args[0])
    true_val = DaxTranslator.translate(args[1])
    false_val = DaxTranslator.translate(args[2]) if len(args) > 2 else "NULL"
    return f"CASE WHEN {cond} THEN {true_val} ELSE {false_val} END"


@DaxTranslator.register_function("AVERAGE")
def _translate_average(args: List[str]) -> str:
    if not args or not args[0]:
        raise ValueError("AVERAGE requires 1 argument")
    arg = DaxTranslator.translate(args[0])
    return f"AVG({arg})"


@DaxTranslator.register_function("COUNTROWS")
def _translate_countrows(args: List[str]) -> str:
    if args and args[0]:
        arg = DaxTranslator.translate(args[0])
        return f"COUNT({arg})"
    return "COUNT(*)"


@DaxTranslator.register_function("CALCULATE")
def _translate_calculate(args: List[str]) -> str:
    if not args or not args[0]:
        return "NULL"
    # KISS: Returns expression. Additional filters are handled by FilterContext/SemanticQueryResolver.
    return DaxTranslator.translate(args[0])


@DaxTranslator.register_function("RELATED")
def _translate_related(args: List[str]) -> str:
    if not args or not args[0]:
        return ""
    # KISS: Returns column. Foreign table joins are resolved by SemanticQueryResolver.
    return DaxTranslator.translate(args[0])
