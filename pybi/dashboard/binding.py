"""Dashboard data binding module linking widgets to Polars DataFrames and DuckDB queries."""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Union

import duckdb
import polars as pl


@dataclass
class WidgetBinding:
    """Dataclass representing a binding between a dashboard widget and a data source or query."""

    widget_id: str
    source_name: str
    query: Optional[str] = None
    callback: Optional[Callable[[pl.DataFrame], None]] = None


class DataBinder:
    """Manager class linking dashboard widgets to Polars DataFrames or DuckDB queries with reactive callbacks."""

    def __init__(self, duckdb_conn: Optional[duckdb.DuckDBPyConnection] = None) -> None:
        """Initialize DataBinder.

        Args:
            duckdb_conn: Optional DuckDB connection instance.
        """
        self.duckdb_conn = duckdb_conn or duckdb.connect(database=":memory:")
        self._sources: Dict[str, pl.DataFrame] = {}
        self._bindings: Dict[str, WidgetBinding] = {}

    def register_source(self, name: str, data: Union[pl.DataFrame, duckdb.DuckDBPyRelation]) -> None:
        """Register or overwrite a data source.

        Args:
            name: Source identifier name.
            data: Polars DataFrame or DuckDB PyRelation.
        """
        if isinstance(data, duckdb.DuckDBPyRelation):
            df = data.pl()
        elif isinstance(data, pl.DataFrame):
            df = data
        else:
            raise TypeError("Data source must be a Polars DataFrame or DuckDBPyRelation.")

        self._sources[name] = df
        self.duckdb_conn.register(name, df)

    def bind_widget(
        self,
        widget_id: str,
        source_name: str,
        query: Optional[str] = None,
        callback: Optional[Callable[[pl.DataFrame], None]] = None,
    ) -> WidgetBinding:
        """Bind a dashboard widget to a data source or query.

        Args:
            widget_id: Unique identifier for the dashboard widget.
            source_name: Name of registered data source.
            query: Optional DuckDB SQL query string (e.g. "SELECT * FROM source_name WHERE ...").
            callback: Optional reactive callback function called when underlying source updates.

        Returns:
            WidgetBinding instance.
        """
        binding = WidgetBinding(
            widget_id=widget_id,
            source_name=source_name,
            query=query,
            callback=callback,
        )
        self._bindings[widget_id] = binding
        return binding

    def unbind_widget(self, widget_id: str) -> None:
        """Remove binding for a widget.

        Args:
            widget_id: Widget identifier.
        """
        self._bindings.pop(widget_id, None)

    def get_source_data(self, source_name: str, query: Optional[str] = None) -> pl.DataFrame:
        """Fetch DataFrame for a data source or DuckDB query.

        Args:
            source_name: Source identifier name.
            query: Optional DuckDB SQL query string.

        Returns:
            pl.DataFrame: The resulting DataFrame.
        """
        if source_name not in self._sources:
            raise KeyError(f"Data source '{source_name}' is not registered.")

        if query:
            return self.duckdb_conn.query(query).pl()
        return self._sources[source_name]

    def get_widget_data(self, widget_id: str) -> pl.DataFrame:
        """Fetch data for a bound widget based on its registered binding.

        Args:
            widget_id: Widget identifier.

        Returns:
            pl.DataFrame: Resulting DataFrame.
        """
        if widget_id not in self._bindings:
            raise KeyError(f"Widget '{widget_id}' is not bound to any data source.")

        binding = self._bindings[widget_id]
        return self.get_source_data(binding.source_name, binding.query)

    def list_sources(self) -> list:
        """List the names of all registered data sources.

        Returns:
            Sorted source names available for widget binding.
        """
        return sorted(self._sources.keys())

    def update_source(self, source_name: str, new_data: Union[pl.DataFrame, duckdb.DuckDBPyRelation]) -> None:
        """Update a registered data source and trigger reactive callbacks for all bound widgets.

        Args:
            source_name: Name of data source to update.
            new_data: Updated Polars DataFrame or DuckDB PyRelation.
        """
        self.register_source(source_name, new_data)

        # Notify bound widgets
        for binding in list(self._bindings.values()):
            if binding.source_name == source_name and binding.callback is not None:
                updated_df = self.get_widget_data(binding.widget_id)
                binding.callback(updated_df)


# Global default binder instance
default_binder = DataBinder()
