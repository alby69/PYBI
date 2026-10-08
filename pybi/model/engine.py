"""ModelEngine wrapping DuckDB columnar store for PyBI Semantic Model."""

from typing import Any, Dict, List, Optional
import duckdb
import polars as pl

from pybi.model.schema import Column, DataType, SemanticModel, Table


class ModelEngine:
    """Manages in-memory DuckDB columnar storage and semantic model registration."""

    def __init__(self, conn: Optional[duckdb.DuckDBPyConnection] = None):
        self.conn = conn or duckdb.connect(database=":memory:")
        self.semantic_model = SemanticModel()

    def register_dataframe(self, table_name: str, df: pl.DataFrame, source_node_id: Optional[str] = None) -> Table:
        """Register a Polars DataFrame into DuckDB and create a semantic Table.

        Args:
            table_name: Table identifier.
            df: Polars DataFrame output from ETL.
            source_node_id: Optional ETL source node id.

        Returns:
            Table: Constructed semantic Table model.
        """
        self.conn.register(table_name, df)

        # Infer columns
        columns = []
        for col_name, dtype in zip(df.columns, df.dtypes):
            dt_str = str(dtype).upper()
            if "INT" in dt_str:
                dt = DataType.INTEGER
            elif "FLOAT" in dt_str or "DECIMAL" in dt_str:
                dt = DataType.FLOAT
            elif "BOOL" in dt_str:
                dt = DataType.BOOLEAN
            elif "DATE" in dt_str and "TIME" not in dt_str:
                dt = DataType.DATE
            elif "TIME" in dt_str or "DATETIME" in dt_str:
                dt = DataType.DATETIME
            else:
                dt = DataType.STRING
            columns.append(Column(name=col_name, data_type=dt))

        table = Table(name=table_name, columns=columns, source_node_id=source_node_id)
        self.semantic_model.add_table(table)
        return table

    def query(self, sql: str) -> pl.DataFrame:
        """Execute a DuckDB SQL query against the semantic model tables.

        Args:
            sql: SQL query string.

        Returns:
            pl.DataFrame: Resulting Polars DataFrame.
        """
        return self.conn.query(sql).pl()

    def list_tables(self) -> List[str]:
        """List registered table names in the model engine."""
        return list(self.semantic_model.tables.keys())
