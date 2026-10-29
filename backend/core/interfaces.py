"""Abstract Base Classes and Protocols for PyBI Decoupled Architecture."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class IDaxTranslator(Protocol):
    """Protocol contract for translating DAX expressions into DuckDB SQL fragments."""

    def translate(self, dax_expression: str, model: Optional[Any] = None) -> str:
        """Translate a DAX expression into a valid DuckDB SQL fragment."""
        ...


@runtime_checkable
class ISemanticQueryResolver(Protocol):
    """Protocol contract for resolving semantic query requests into complete SQL queries."""

    def resolve(
        self,
        measures: List[str],
        dimensions: List[str],
        filters: Dict[str, Any],
        model: Any,
    ) -> str:
        """Generate a complete SQL query, injecting automatic JOINs based on relationships."""
        ...


@runtime_checkable
class IStorage(Protocol):
    """Protocol contract for project storage operations."""

    def load_project(self, project_id: str) -> Dict[str, Any]:
        """Load project configuration and metadata."""
        ...

    def save_project(self, project_id: str, data: Dict[str, Any]) -> None:
        """Save project configuration and metadata."""
        ...


class ETLNode(ABC):
    """Abstract Base Class for ETL pipeline nodes supporting Query Folding via Ibis."""

    @property
    def node_id(self) -> str:
        """Unique node identifier in the DAG."""
        return getattr(self, "_node_id", getattr(self, "id", "unknown_node"))

    @property
    def foldable(self) -> bool:
        """Whether this node can participate in SQL query folding via Ibis."""
        return True

    def to_ibis_expr(self, input_expr: Any) -> Any:
        """Translate this node's transformation logic into an Ibis table expression."""
        raise NotImplementedError(
            f"Node '{self.node_id}' does not implement to_ibis_expr()"
        )

    def validate(self) -> List[str]:
        """Validate node configuration and input parameters."""
        return []

    def to_sql_expr(self, input_table: str) -> str:
        """Generate SQL CTE expression for this node given an input table name."""
        return f"SELECT * FROM {input_table}"

    def to_polars_expr(self, input_lazyframe: Any) -> Any:
        """Apply transformation on a Polars LazyFrame."""
        return input_lazyframe

    def execute(self, input_data: Any, context: Optional[Dict[str, Any]] = None) -> Any:
        """Optional direct execution method for fallback or non-foldable node execution."""
        return input_data


class Visual(ABC):
    """Abstract Base Class for individual visual charts and tables."""

    @abstractmethod
    def generate_query(self, filter_context: Optional[Any] = None) -> str:
        """Generate SQL query to fetch visual data, respecting current filter context."""
        pass


class Publisher(ABC):
    """Abstract Base Class for exporting and publishing reports."""

    @abstractmethod
    def export_to_html(self, project_id: str, output_path: Optional[str] = None) -> str:
        """Export project dashboard to a static standalone HTML file."""
        pass

    @abstractmethod
    def export_to_pdf(self, project_id: str, output_path: Optional[str] = None) -> str:
        """Export project dashboard to a PDF document."""
        pass
