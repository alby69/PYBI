"""Output ETL node implementation."""

from typing import Any, Dict, List
from .base import BaseETLNode


class OutputNode(BaseETLNode):
    """Output node destination definition."""

    def validate(self) -> List[str]:
        table_name = self.data.get("table_name")
        if not table_name:
            return [f"Output node '{self.node_id}' missing table_name."]
        return []

    def to_sql_expr(self, input_table: str) -> str:
        return f"SELECT * FROM {input_table}"
