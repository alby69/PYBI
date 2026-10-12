"""Semantic Layer models for PyBI (Dimensions, Measures, SemanticModel, Queries, and Core Schema Integration)."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from pybi.core.semantic_model import (
    Cardinality,
    JoinType,
    RLSRule,
    SemanticColumn as Dimension,
    SemanticMeasure as Measure,
    SemanticModel as CoreSemanticModel,
    SemanticRelationship,
    SemanticTable,
)


class SemanticModel(BaseModel):
    """Legacy and single-table / multi-table semantic model wrapper."""

    name: str = Field(..., description="Name of the semantic model")
    source_table: str = Field("source_table", description="Source table or view name in DuckDB/binder")
    dimensions: List[Dimension] = Field(default_factory=list, description="Defined dimensions/columns")
    measures: List[Measure] = Field(default_factory=list, description="Defined measures")
    tables: List[SemanticTable] = Field(default_factory=list, description="Tables for multi-table models")
    relationships: List[SemanticRelationship] = Field(default_factory=list, description="Defined table relationships")
    rls_rules: List[RLSRule] = Field(default_factory=list, description="Row-level security rules")

    def to_core_model(self) -> CoreSemanticModel:
        """Convert to CoreSemanticModel representation."""
        tables = list(self.tables)
        if not tables and self.source_table:
            tables = [
                SemanticTable(
                    name=self.name,
                    source_table=self.source_table,
                    columns=self.dimensions,
                    measures=self.measures,
                )
            ]
        return CoreSemanticModel(
            name=self.name,
            tables=tables,
            relationships=self.relationships,
            rls_rules=self.rls_rules,
            default_table=self.source_table,
        )


class SemanticQueryRequest(BaseModel):
    """Payload for requesting semantic query execution."""

    model_name: Optional[str] = Field(default=None, description="Optional target semantic model name")
    source_table: Optional[str] = Field(default=None, description="Source table if model_name is omitted")
    dimensions: List[str] = Field(default_factory=list, description="Dimension names or columns to group by")
    measures: List[str] = Field(default_factory=list, description="Measure names or aggregation expressions to compute")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Active filter context e.g. {'region': 'North', 'amount': {'>=': 100}}")
    limit: Optional[int] = Field(default=1000, description="Max rows to return")


class SemanticQueryResponse(BaseModel):
    """Response containing semantic query results and generated SQL."""

    columns: List[str] = Field(default_factory=list)
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    generated_sql: str = Field("")
    row_count: int = Field(0)
