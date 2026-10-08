"""Abstract Base Classes for PyBI Decoupled Architecture."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class ETLNode(ABC):
    """Abstract Base Class for ETL pipeline nodes."""

    @abstractmethod
    def validate(self) -> List[str]:
        """Validate node configuration and input parameters.

        Returns:
            List[str]: List of validation error messages (empty if valid).
        """
        pass

    @abstractmethod
    def to_sql_expr(self, input_table: str) -> str:
        """Generate SQL CTE expression for this node given an input table name.

        Args:
            input_table: Name of the input SQL table or CTE.

        Returns:
            str: SQL query string representing this transformation.
        """
        pass

    @abstractmethod
    def to_polars_expr(self, input_lazyframe: Any) -> Any:
        """Apply transformation on a Polars LazyFrame.

        Args:
            input_lazyframe: Polars LazyFrame.

        Returns:
            Polars LazyFrame with transformation applied.
        """
        pass


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
