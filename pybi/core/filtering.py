"""Shared SQL filter clause construction."""

from typing import Any, Dict, List, Optional, Set, Tuple


def build_where_clauses(
    filters: Dict[str, Any],
    valid_columns: Optional[Set[str]] = None,
    quote_columns: bool = True,
) -> Tuple[List[str], List[Any]]:
    """Convert scalar, list, and comparison filters into SQL conditions."""
    clauses: List[str] = []
    for column, value in filters.items():
        if valid_columns and column not in valid_columns:
            continue

        safe_column = (
            '"' + str(column).replace('"', '""') + '"'
            if quote_columns
            else str(column)
        )
        if isinstance(value, dict):
            for operator, operand in value.items():
                if operator in (">=", "<=", ">", "<", "=", "!=", "<>"):
                    clauses.append(f"{safe_column} {operator} {_sql_literal(operand)}")
        elif isinstance(value, (list, tuple, set)):
            values = sorted(value) if isinstance(value, set) else value
            if values:
                literals = ", ".join(_sql_literal(item) for item in values)
                clauses.append(f"{safe_column} IN ({literals})")
        elif value is not None and str(value).strip():
            clauses.append(f"{safe_column} = {_sql_literal(value)}")

    return clauses, []


def _sql_literal(value: Any) -> str:
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    return str(value)
