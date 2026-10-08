"""Abstract Base Classes for PyBI Decoupled Architecture."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


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
        """Translate this node's transformation logic into an Ibis table expression.

        Args:
            input_expr: Upstream Ibis Table expression.

        Returns:
            Transformed Ibis Table expression.
        """
        raise NotImplementedError(
            f"Node '{self.node_id}' does not implement to_ibis_expr()"
        )

    def validate(self) -> List[str]:
        """Validate node configuration and input parameters.

        Returns:
            List[str]: List of validation error messages (empty if valid).
        """
        return []

    def to_sql_expr(self, input_table: str) -> str:
        """Generate SQL CTE expression for this node given an input table name.

        Args:
            input_table: Name of the input SQL table or CTE.

        Returns:
            str: SQL query string representing this transformation.
        """
        return f"SELECT * FROM {input_table}"

    def to_polars_expr(self, input_lazyframe: Any) -> Any:
        """Apply transformation on a Polars LazyFrame.

        Args:
            input_lazyframe: Polars LazyFrame.

        Returns:
            Polars LazyFrame with transformation applied.
        """
        return input_lazyframe


class Visual(ABC):
    """Abstract Base Class for individual visual charts and tables."""

    @abstractmethod
    def generate_query(self, filter_context: Optional[Any] = None) -> str:
        """Generate SQL query to fetch visual data, respecting current filter context.

        Args:
            filter_context: Optional FilterContext containing active cross-filters.

        Returns:
            str: DuckDB SQL query string.
        """
        pass


class Publisher(ABC):
    """Abstract Base Class for exporting and publishing reports."""

    @abstractmethod
    def export_to_html(self, project_id: str, output_path: Optional[str] = None) -> str:
        """Export project dashboard to a static standalone HTML file.

        Args:
            project_id: Unique project identifier.
            output_path: Optional output file path.

        Returns:
            str: Path to generated HTML file.
        """
        pass

    @abstractmethod
    def export_to_pdf(self, project_id: str, output_path: Optional[str] = None) -> str:
        """Export project dashboard to a PDF document.

        Args:
            project_id: Unique project identifier.
            output_path: Optional output file path.

        Returns:
            str: Path to generated PDF file.
        """
        pass
