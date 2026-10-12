"""ModelEngine wrapping DuckDB columnar store for PyBI Semantic Model."""

from typing import Any, Dict, List, Optional
import duckdb
import polars as pl

from pybi.model.schema import Column, DataType, SemanticModel, Table


class ModelEngine:
    """Manages in-memory DuckDB columnar storage, semantic model tables, and calculated measures."""

    def __init__(self, conn: Optional[duckdb.DuckDBPyConnection] = None):
        self.conn = conn or duckdb.connect(database=":memory:")
        self.tables: Dict[str, Table] = {}
        self.measures: Dict[str, Any] = {}
        self.semantic_model = SemanticModel()

    def register_table(self, table: Table) -> None:
        """Register a semantic Table into the engine."""
        self.tables[table.name] = table
        self.semantic_model.add_table(table)

    def register_measure(self, measure: Any) -> None:
        """Register a calculated Measure into the engine."""
        self.measures[measure.name] = measure

    def evaluate_measure(self, measure_name: str, filter_context: Any) -> float:
        """Evaluate a measure using DuckDB SQL applying the current FilterContext."""
        if measure_name not in self.measures:
            raise KeyError(f"Measure '{measure_name}' not found.")

        measure = self.measures[measure_name]
        sql_expr = measure.to_sql_fragment()

        table = self.tables.get(measure.table_name)
        if table and hasattr(filter_context, "to_sql_where"):
            where_clause = filter_context.to_sql_where(table)
        else:
            where_clause = ""

        if where_clause and not where_clause.startswith("WHERE"):
            where_clause = f"WHERE {where_clause}"

        query = f"SELECT {sql_expr} AS result FROM {measure.table_name} {where_clause}".strip()
        result = self.conn.execute(query).fetchone()

        if result and result[0] is not None:
            return float(result[0])
        return 0.0

    def register_dataframe(self, table_name: str, df: pl.DataFrame, source_node_id: Optional[str] = None) -> Table:
        """Register a Polars DataFrame into DuckDB and create a semantic Table."""
        self.conn.register(table_name, df)

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
        self.register_table(table)
        return table

    def query(self, sql: str) -> pl.DataFrame:
        """Execute a DuckDB SQL query against the semantic model tables."""
        return self.conn.query(sql).pl()

    def list_tables(self) -> List[str]:
        """List registered table names in the model engine."""
        return list(self.tables.keys())
