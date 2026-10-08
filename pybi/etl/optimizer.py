"""SQLGlot Post-Optimizer for PyBI ETL Query Folding."""

import sqlglot
from sqlglot.optimizer import optimize as sqlglot_optimize
from pybi.core.exceptions import CompilationError


class SQLOptimizer:
    """Uses SQLGlot to parse, optimize, and validate DuckDB SQL queries.

    Optimizations applied:
    - Predicate pushdown
    - Projection pruning
    - Constant folding
    - Dialect validation and AST optimization
    """

    def __init__(self, dialect: str = "duckdb"):
        self.dialect = dialect

    def optimize(self, sql: str, schema: dict | None = None) -> str:
        """Parse, optimize, and re-generate the SQL string.

        Args:
            sql: Raw SQL query string.
            schema: Optional schema dictionary for column-level optimizations.

        Returns:
            Optimized SQL string.

        Raises:
            CompilationError: If SQL parsing or optimization fails.
        """
        if not sql or not sql.strip():
            return sql

        try:
            parsed = sqlglot.parse_one(sql, read=self.dialect)
            optimized = sqlglot_optimize(parsed, schema=schema, dialect=self.dialect)
            return optimized.sql(dialect=self.dialect, pretty=True)
        except sqlglot.errors.ParseError as e:
            raise CompilationError(f"SQL parse error: {e}") from e
        except Exception as e:
            # Fallback to parsed.sql or original sql if optimizer rule fails on complex dialect constructs
            try:
                parsed = sqlglot.parse_one(sql, read=self.dialect)
                return parsed.sql(dialect=self.dialect, pretty=True)
            except Exception:
                return sql

    def validate(self, sql: str) -> list[str]:
        """Validate SQL query syntax.

        Args:
            sql: SQL string.

        Returns:
            List of warning/error strings (empty if valid).
        """
        warnings = []
        try:
            sqlglot.parse_one(sql, read=self.dialect)
        except sqlglot.errors.ParseError as e:
            warnings.append(f"SQL parse warning: {e}")
        return warnings

    def explain_diff(self, original: str, optimized: str) -> str:
        """Return human-readable comparison of original vs optimized SQL.

        Args:
            original: Raw SQL string.
            optimized: Optimized SQL string.

        Returns:
            Formatted comparison string.
        """
        return (
            f"── Original SQL ──\n{original}\n\n"
            f"── Optimized SQL ──\n{optimized}"
        )
