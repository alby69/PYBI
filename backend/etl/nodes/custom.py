"""Custom Python transformation ETL node (Non-foldable)."""

from typing import Any, Callable, Dict, List
import ibis.expr.types as ir
import polars as pl
from pybi.core.exceptions import ValidationError
from .base import BaseETLNode


class CustomPythonNode(BaseETLNode):
    """A node that runs arbitrary Python/Polars code.

    CANNOT be folded into SQL — acts as a materialization boundary.
    """

    def __init__(
        self,
        node_id: str,
        transform_fn: Callable[[pl.DataFrame], pl.DataFrame] | None = None,
        data: Dict[str, Any] | None = None,
    ):
        super().__init__(node_id, data or {})
        self.transform_fn = transform_fn or self.data.get("transform_fn")

    @property
    def foldable(self) -> bool:
        return False

    def validate(self) -> List[str]:
        if self.transform_fn is not None and not callable(self.transform_fn):
            return [f"CustomPythonNode '{self.node_id}' transform_fn must be callable."]
        return []

    def to_ibis_expr(self, input_expr: ir.Table) -> ir.Table:
        raise NotImplementedError(
            f"CustomPythonNode '{self.node_id}' cannot produce an Ibis expression. "
            "The compiler must materialize upstream results first."
        )
