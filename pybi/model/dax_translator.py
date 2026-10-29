"""DAX expression translator for PyBI Semantic Model."""

from typing import Any, Callable, List, Optional
from backend.core.dax_engine import DaxEngine


class DaxTranslator:
    """
    Translates DAX-like expressions into DuckDB SQL query fragments.
    Delegates directly to DaxEngine to ensure a unified registry and translation logic.
    """

    @classmethod
    def register_function(cls, dax_func: str):
        """Decorator to register a DAX function translator."""
        return DaxEngine.register(dax_func)

    @classmethod
    def translate(cls, expression: str, model: Optional[Any] = None) -> str:
        """Translate a DAX-like expression into DuckDB SQL fragment."""
        return DaxEngine.translate(expression, model=model)

    @staticmethod
    def _parse_args(args_str: str) -> List[str]:
        """Splits arguments by comma, respecting nested parentheses and quotes."""
        return DaxEngine._parse_args(args_str)
