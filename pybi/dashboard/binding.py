"""Dashboard data binding module linking widgets to Polars DataFrames, DuckDB queries, and Semantic Models."""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Union

import duckdb
import polars as pl

from pybi.core.semantic_model import SemanticModel as CoreSemanticModel
from pybi.semantic.engine import SemanticQueryResolver
from pybi.semantic.models import SemanticModel, SemanticQueryRequest, SemanticQueryResponse


@dataclass
class WidgetBinding:
    """Dataclass representing a binding between a dashboard widget and a data source or query."""

    widget_id: str
    source_name: str
    query: Optional[str] = None
    callback: Optional[Callable[[pl.DataFrame], None]] = None


class DataBinder:
    """Manager class linking dashboard widgets to Polars DataFrames, DuckDB queries, or Semantic Models with reactive callbacks."""

    def __init__(self, duckdb_conn: Optional[duckdb.DuckDBPyConnection] = None) -> None:
        """Initialize DataBinder.

        Args:
            duckdb_conn: Optional DuckDB connection instance.
        """
        self.duckdb_conn = duckdb_conn or duckdb.connect(database=":memory:")
        self._sources: Dict[str, pl.DataFrame] = {}
        self._bindings: Dict[str, WidgetBinding] = {}
        self.semantic_resolver = SemanticQueryResolver(self.duckdb_conn)

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

    def register_semantic_model(self, model: Union[SemanticModel, CoreSemanticModel]) -> None:
        """Register a semantic model in the underlying resolver."""
        self.semantic_resolver.register_model(model)

    def query_semantic(self, request: SemanticQueryRequest) -> pl.DataFrame:
        """Execute a semantic query request and return a Polars DataFrame."""
        response = self.semantic_resolver.execute(request)
        if not response.rows:
            return pl.DataFrame({col: [] for col in response.columns})
        return pl.from_dicts(response.rows)

    def bind_widget(
        self,
        widget_id: str,
        source_name: str,
        query: Optional[str] = None,
        callback: Optional[Callable[[pl.DataFrame], None]] = None,
    ) -> WidgetBinding:
        """Bind a dashboard widget to a data source or query."""
        binding = WidgetBinding(
            widget_id=widget_id,
            source_name=source_name,
            query=query,
            callback=callback,
        )
        self._bindings[widget_id] = binding
        return binding

    def unbind_widget(self, widget_id: str) -> None:
        """Remove binding for a widget."""
        self._bindings.pop(widget_id, None)

    def get_source_data(self, source_name: str, query: Optional[str] = None) -> pl.DataFrame:
        """Fetch DataFrame for a data source or DuckDB query."""
        if source_name not in self._sources:
            # Check if source_name is a registered semantic model
            m = self.semantic_resolver.get_model(source_name)
            if m:
                req = SemanticQueryRequest(model_name=source_name, dimensions=[], measures=[])
                return self.query_semantic(req)
            raise KeyError(f"Data source or semantic model '{source_name}' is not registered.")

        if query:
            return self.duckdb_conn.query(query).pl()
        return self._sources[source_name]

    def get_widget_data(self, widget_id: str) -> pl.DataFrame:
        """Fetch data for a bound widget based on its registered binding."""
        if widget_id not in self._bindings:
            raise KeyError(f"Widget '{widget_id}' is not bound to any data source.")

        binding = self._bindings[widget_id]
        return self.get_source_data(binding.source_name, binding.query)

    def list_sources(self) -> list:
        """List the names of all registered data sources and semantic models."""
        sources = set(self._sources.keys())
        sources.update(self.semantic_resolver.registry.keys())
        return sorted(list(sources))

    def update_source(self, source_name: str, new_data: Union[pl.DataFrame, duckdb.DuckDBPyRelation]) -> None:
        """Update a registered data source and trigger reactive callbacks for all bound widgets."""
        self.register_source(source_name, new_data)

        # Notify bound widgets
        for binding in list(self._bindings.values()):
            if binding.source_name == source_name and binding.callback is not None:
                updated_df = self.get_widget_data(binding.widget_id)
                binding.callback(updated_df)


# Global default binder instance
default_binder = DataBinder()
