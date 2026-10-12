"""Abstract Base Connector interface for PyBI ETL and DirectQuery sources."""

from abc import ABC, abstractmethod
from typing import Any

import polars as pl


class BaseConnector(ABC):
    """Abstract base class defining standardized interface for external data connectors."""

    def __init__(self, connection_uri: str | None = None, **kwargs: Any) -> None:
        self.connection_uri = connection_uri or ""
        self.config = kwargs

    @abstractmethod
    def test_connection(self) -> bool:
        """Test connectivity to external datasource.

        Returns:
            bool: True if connection test succeeds, False otherwise.
        """

    @abstractmethod
    def get_schema(self, table_name: str | None = None) -> dict[str, Any]:
        """Fetch schema metadata for specified table or default target.

        Returns:
            Dict[str, Any]: Schema description dictionary with column names and types.
        """

    @abstractmethod
    def read(self, query_or_table: str, **kwargs: Any) -> pl.DataFrame:
        """Read data into Polars DataFrame.

        Args:
            query_or_table: Table name or SQL query to execute.

        Returns:
            pl.DataFrame: Resulting DataFrame.
        """

    @abstractmethod
    def write(self, df: pl.DataFrame, table_name: str, if_exists: str = "replace", **kwargs: Any) -> None:
        """Write Polars DataFrame to target dataset/table.

        Args:
            df: DataFrame to write.
            table_name: Target table identifier.
            if_exists: Behavior if table exists ('replace', 'append', 'fail').
        """

    @abstractmethod
    def direct_query(self, query: str, **kwargs: Any) -> pl.DataFrame:
        """Execute a live DirectQuery passthrough against target external engine.

        Args:
            query: Live SQL query string.

        Returns:
            pl.DataFrame: Query result set.
        """
