"""Base ETL node class."""

from typing import Any, Dict, List
import polars as pl
from pybi.core.interfaces import ETLNode


class BaseETLNode(ETLNode):
    """Base class for concrete ETL nodes."""

    def __init__(self, node_id: str, data: Dict[str, Any]):
        self.node_id = node_id
        self.data = data

    def validate(self) -> List[str]:
        return []

    def to_sql_expr(self, input_table: str) -> str:
        return f"SELECT * FROM {input_table}"

    def to_polars_expr(self, input_lazyframe: pl.LazyFrame) -> pl.LazyFrame:
        return input_lazyframe
