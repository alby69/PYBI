"""Filter Context processing for PyBI Semantic Layer."""

from typing import Any, Dict, List, Optional, Tuple


def build_where_clauses(filters: Dict[str, Any], valid_columns: Optional[set] = None) -> Tuple[List[str], List[Any]]:
    """Convert a filter context dictionary into parameterized or sanitized SQL WHERE clause conditions.

    Supported filter values:
    - Scalar value: e.g. {'region': 'North'} -> '"region" = \'North\''
    - List of values: e.g. {'category': ['A', 'B']} -> '"category" IN (\'A\', \'B\')'
    - Operator dict: e.g. {'amount': {'>=': 100, '<': 500}} -> '"amount" >= 100 AND "amount" < 500'
    """
    clauses: List[str] = []

    if not filters:
        return clauses, []

    for col, val in filters.items():
        if valid_columns and col not in valid_columns:
            continue

        safe_col = f'"{col}"'

        if isinstance(val, dict):
            for op, op_val in val.items():
                if op in (">=", "<=", ">", "<", "=", "!=", "<>"):
                    if isinstance(op_val, str):
                        escaped = op_val.replace("'", "''")
                        safe_val = f"'{escaped}'"
                    else:
                        safe_val = str(op_val)
                    clauses.append(f"{safe_col} {op} {safe_val}")
        elif isinstance(val, (list, tuple, set)):
            val_list = list(val)
            if not val_list:
                continue
            formatted_vals = []
            for v in val_list:
                if isinstance(v, str):
                    escaped = v.replace("'", "''")
                    formatted_vals.append(f"'{escaped}'")
                else:
                    formatted_vals.append(str(v))
            clauses.append(f"{safe_col} IN ({', '.join(formatted_vals)})")
        elif val is not None and str(val).strip() != "":
            if isinstance(val, str):
                escaped = val.replace("'", "''")
                safe_val = f"'{escaped}'"
            else:
                safe_val = str(val)
            clauses.append(f"{safe_col} = {safe_val}")

    return clauses, []
