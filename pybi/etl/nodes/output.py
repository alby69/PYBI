"""Output ETL node implementation."""

import re
from typing import Any, Dict, List, Optional, Tuple
import polars as pl

from pybi.etl.connectors.writers import WriterRegistry
from .base import BaseETLNode


class OutputNode(BaseETLNode):
    """Output node destination definition."""

    def validate(self) -> List[str]:
        table_name = self.data.get("table_name")
        label = self.data.get("label", "")
        if not table_name and label:
            match = re.search(r"\(([^)]+)\)", label)
            if match:
                table_name = match.group(1)
        if not table_name and not self.node_id:
            return [f"Output node '{self.node_id}' missing table_name."]
        return []

    def to_sql_expr(self, input_table: str) -> str:
        return f"SELECT * FROM {input_table}"

    def execute(
        self,
        input_data: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, Tuple[str, pl.DataFrame]]:
        """Execute output destination writing using WriterRegistry.

        Args:
            input_data: Polars DataFrame to export.
            context: Execution context containing options such as 'duckdb_conn'.

        Returns:
            Tuple[str, Tuple[str, pl.DataFrame]]: (log_message, (table_name, df))
        """
        ctx = context or {}
        duckdb_conn = ctx.get("duckdb_conn")

        data = self.data
        table_name = data.get("table_name")
        label = data.get("label", "")
        if not table_name and label:
            match = re.search(r"\(([^)]+)\)", label)
            if match:
                table_name = match.group(1)
        if not table_name:
            table_name = f"output_{self.node_id}"

        output_type = data.get("output_type") or data.get("destination_type") or ""
        filepath_or_uri = data.get("file_path") or data.get("path") or data.get("filepath") or data.get("uri") or ""

        df = input_data if isinstance(input_data, pl.DataFrame) else pl.DataFrame(input_data)

        return WriterRegistry.write(
            df=df,
            table_name=table_name,
            output_type=output_type,
            filepath_or_uri=filepath_or_uri,
            duckdb_conn=duckdb_conn,
        )
