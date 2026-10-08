"""Centralized FilterContext for dashboard interaction and cross-filtering propagation."""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class FilterRule:
    """Filter rule applied to a table and column."""

    table: str
    column: str
    value: Any
    operator: str = "="


class FilterContext:
    """Observer pattern manager for slicers and cross-filtering propagation across visuals."""

    def __init__(self) -> None:
        self.filters: Dict[str, FilterRule] = {}
        self._subscribers: List[Callable[['FilterContext'], None]] = []

    def add_filter(self, table: str, column: str, value: Any, operator: str = "=") -> None:
        """Add or update a filter rule and notify subscribers.

        Args:
            table: Target table name.
            column: Target column name.
            value: Filter value.
            operator: SQL comparison operator (default '=').
        """
        key = f"{table}.{column}"
        self.filters[key] = FilterRule(table=table, column=column, value=value, operator=operator)
        self.notify()

    def remove_filter(self, table: str, column: str) -> None:
        """Remove a filter rule for a specific table and column.

        Args:
            table: Target table name.
            column: Target column name.
        """
        key = f"{table}.{column}"
        if key in self.filters:
            del self.filters[key]
            self.notify()

    def clear_filters(self) -> None:
        """Clear all active filter rules."""
        if self.filters:
            self.filters.clear()
            self.notify()

    def subscribe(self, callback: Callable[['FilterContext'], None]) -> None:
        """Subscribe a listener callback to filter context changes."""
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[['FilterContext'], None]) -> None:
        """Unsubscribe a listener callback."""
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def notify(self) -> None:
        """Notify all registered subscribers of state updates."""
        for callback in self._subscribers:
            callback(self)

    def to_sql_where(self, table_name: Optional[str] = None) -> str:
        """Build SQL WHERE clause for filters matching the table name.

        Args:
            table_name: Optional filter table name constraint.

        Returns:
            str: SQL WHERE conditions joined by AND (empty string if no filters).
        """
        clauses = []
        for rule in self.filters.values():
            if table_name and rule.table != table_name:
                continue
            val_repr = f"'{rule.value}'" if isinstance(rule.value, str) else str(rule.value)
            clauses.append(f"{rule.column} {rule.operator} {val_repr}")

        return " AND ".join(clauses) if clauses else ""
