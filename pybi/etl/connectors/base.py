"""Abstract Base Connector interface for Phase 6 Enterprise Connectors."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import polars as pl


class BaseConnector(ABC):
    """Abstract Base Class for Enterprise Data Connectors."""

    def __init__(self, connection_config: Dict[str, Any]):
        self.config = connection_config

    @abstractmethod
    def test_connection(self) -> bool:
        """Test database connection health."""
        pass

    @abstractmethod
    def read(self, query_or_table: str, limit: Optional[int] = None) -> pl.DataFrame:
        """Read data into a Polars DataFrame."""
        pass

    @abstractmethod
    def write(self, df: pl.DataFrame, table_name: str, mode: str = "append") -> bool:
        """Write a Polars DataFrame to target database."""
        pass

    @abstractmethod
    def get_schema(self, table_name: str) -> Dict[str, str]:
        """Fetch schema column types dict."""
        pass

    @abstractmethod
    def direct_query(self, sql_query: str) -> pl.DataFrame:
        """Execute live DirectQuery on external source database."""
        pass
