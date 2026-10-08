"""Base ETL node class."""

from typing import Any, Dict, List
import ibis.expr.types as ir
import polars as pl
from pybi.core.interfaces import ETLNode


class BaseETLNode(ETLNode):
    """Base class for concrete ETL nodes."""

    def __init__(self, node_id: str, data: Dict[str, Any] | None = None):
        self._node_id = node_id
        self.data = data if data is not None else {}

    @property
    def node_id(self) -> str:
        return self._node_id

    @property
    def foldable(self) -> bool:
        return True

    def validate(self) -> List[str]:
        return []

    def to_ibis_expr(self, input_expr: ir.Table) -> ir.Table:
        return input_expr

    def to_sql_expr(self, input_table: str) -> str:
        return f"SELECT * FROM {input_table}"

    def to_polars_expr(self, input_lazyframe: pl.LazyFrame) -> pl.LazyFrame:
        return input_lazyframe
