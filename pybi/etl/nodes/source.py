"""Data source ETL node implementation."""

from typing import Any, Dict, List, Optional
import ibis.expr.types as ir
import polars as pl
from .base import BaseETLNode


class DataSourceNode(BaseETLNode):
    """Data source node (CSV, Parquet, SQLite, Postgres)."""

    def validate(self) -> List[str]:
        errors = []
        filepath = self.data.get("file_path") or self.data.get("path")
        if not filepath and self.data.get("source_type") != "postgres":
            errors.append(f"DataSource node '{self.node_id}' missing file_path.")
        return errors

    def to_ibis_expr(self, input_expr: Optional[ir.Table] = None) -> ir.Table:
        if input_expr is not None:
            return input_expr
        return super().to_ibis_expr(input_expr)

    def to_sql_expr(self, input_table: str = "") -> str:
        source_type = (self.data.get("source_type") or "csv").lower()
        filepath = self.data.get("file_path") or self.data.get("path") or ""

        if source_type == "csv":
            sep = self.data.get("csv_separator") or "auto"
            if sep == "auto" or sep == "comma" or sep == ",":
                return f"SELECT * FROM read_csv_auto('{filepath}')"
            elif sep in ("semicolon", ";"):
                return f"SELECT * FROM read_csv_auto('{filepath}', delim=';')"
            elif sep in ("tab", "\t"):
                return f"SELECT * FROM read_csv_auto('{filepath}', delim='\t')"
            elif sep in ("pipe", "|"):
                return f"SELECT * FROM read_csv_auto('{filepath}', delim='|')"
            return f"SELECT * FROM read_csv_auto('{filepath}')"
        elif source_type == "parquet":
            return f"SELECT * FROM read_parquet('{filepath}')"
        elif source_type == "sqlite":
            query = self.data.get("query") or self.data.get("table_name") or "SELECT * FROM sqlite_master"
            return f"SELECT * FROM sqlite_scan('{filepath}', '{query}')"
        return f"SELECT * FROM '{filepath}'"

    def to_polars_expr(self, input_lazyframe: Optional[pl.LazyFrame] = None) -> pl.LazyFrame:
        source_type = (self.data.get("source_type") or "csv").lower()
        filepath = self.data.get("file_path") or self.data.get("path") or ""

        if source_type == "csv":
            sep = self.data.get("csv_separator") or "auto"
            delimiter = ","
            if sep in ("semicolon", ";"):
                delimiter = ";"
            elif sep in ("tab", "\t"):
                delimiter = "\t"
            elif sep in ("pipe", "|"):
                delimiter = "|"
            return pl.scan_csv(filepath, separator=delimiter)
        elif source_type == "parquet":
            return pl.scan_parquet(filepath)
        return pl.LazyFrame()


SourceNode = DataSourceNode
