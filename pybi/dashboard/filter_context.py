"""Centralized FilterContext for dashboard interaction and cross-filtering propagation."""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Union

from pybi.core.filtering import build_where_clauses


@dataclass
class FilterState:
    """Filter state applied to a table and column."""

    table: str
    column: str
    values: List[Any]
    operator: str = "IN"


# Alias for backward compatibility
FilterRule = FilterState


class FilterContext:
    """Centralized filter state manager and observer pattern subject for cross-filtering."""

    def __init__(self) -> None:
        self._active_filters: Dict[str, FilterState] = {}
        self._listeners: List[Callable] = []

    @property
    def filters(self) -> Dict[str, FilterState]:
        """Expose active filters mapping."""
        return self._active_filters

    def set_filter(self, table: str, column: str, values: List[Any], operator: str = "IN") -> None:
        """Set or update a filter state for a table and column."""
        key = f"{table}.{column}"
        self._active_filters[key] = FilterState(table=table, column=column, values=values, operator=operator)
        self._notify_listeners()

    def add_filter(self, table: str, column: str, value: Any, operator: str = "=") -> None:
        """Add or update a filter rule (backward compatibility method)."""
        vals = value if isinstance(value, list) else [value]
        op = "IN" if isinstance(value, list) and operator == "=" else operator
        self.set_filter(table, column, vals, operator=op)

    def clear_filter(self, table: str, column: str) -> None:
        """Clear a specific filter for a table and column."""
        key = f"{table}.{column}"
        if key in self._active_filters:
            del self._active_filters[key]
            self._notify_listeners()

    def remove_filter(self, table: str, column: str) -> None:
        """Remove a specific filter (backward compatibility alias)."""
        self.clear_filter(table, column)

    def clear_filters(self) -> None:
        """Clear all active filter states."""
        if self._active_filters:
            self._active_filters.clear()
            self._notify_listeners()

    def get_active_filters_for_table(self, table_name: str) -> List[FilterState]:
        """Return active filter states for a specific table."""
        return [f for key, f in self._active_filters.items() if f.table == table_name]

    def to_sql_where(self, table: Optional[Union[Any, str]] = None) -> str:
        """Generate a SQL WHERE clause for DuckDB/Polars based on active filters."""
        t_name = None
        if isinstance(table, str):
            t_name = table
        elif table is not None and hasattr(table, "name"):
            t_name = table.name

        if t_name:
            filters = self.get_active_filters_for_table(t_name)
        else:
            filters = list(self._active_filters.values())

        filter_values: Dict[str, Any] = {}
        for f in filters:
            if f.operator == "IN":
                filter_values[f.column] = f.values
            else:
                filter_values[f.column] = {f.operator: f.values[0]} if f.values else {}

        conditions, _ = build_where_clauses(filter_values, quote_columns=False)
        return "WHERE " + " AND ".join(conditions) if conditions else ""

    def subscribe(self, listener: Callable) -> None:
        """Register a subscriber listener callback."""
        if listener not in self._listeners:
            self._listeners.append(listener)

    def unsubscribe(self, listener: Callable) -> None:
        """Unsubscribe a listener callback."""
        if listener in self._listeners:
            self._listeners.remove(listener)

    def _notify_listeners(self) -> None:
        """Notify all subscribed listeners that active filters changed."""
        for listener in list(self._listeners):
            try:
                listener(self._active_filters)
            except (AttributeError, TypeError):
                listener(self)

    def notify(self) -> None:
        """Explicitly notify listeners."""
        self._notify_listeners()
