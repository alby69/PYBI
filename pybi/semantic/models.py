"""Semantic Layer models for PyBI (Dimensions, Measures, SemanticModel, Queries, and Core Schema Integration)."""

from typing import Any

from pydantic import BaseModel, Field

from pybi.core.semantic_model import (
    RLSRule,
    SemanticRelationship,
    SemanticTable,
)
from pybi.core.semantic_model import (
    SemanticColumn as Dimension,
)
from pybi.core.semantic_model import (
    SemanticMeasure as Measure,
)
from pybi.core.semantic_model import (
    SemanticModel as CoreSemanticModel,
)


class SemanticModel(BaseModel):
    """Legacy and single-table / multi-table semantic model wrapper."""

    name: str = Field(..., description="Name of the semantic model")
    source_table: str = Field("source_table", description="Source table or view name in DuckDB/binder")
    dimensions: list[Dimension] = Field(default_factory=list, description="Defined dimensions/columns")
    measures: list[Measure] = Field(default_factory=list, description="Defined measures")
    tables: list[SemanticTable] = Field(default_factory=list, description="Tables for multi-table models")
    relationships: list[SemanticRelationship] = Field(default_factory=list, description="Defined table relationships")
    rls_rules: list[RLSRule] = Field(default_factory=list, description="Row-level security rules")

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

    model_name: str | None = Field(default=None, description="Optional target semantic model name")
    source_table: str | None = Field(default=None, description="Source table if model_name is omitted")
    dimensions: list[str] = Field(default_factory=list, description="Dimension names or columns to group by")
    measures: list[str] = Field(default_factory=list, description="Measure names or aggregation expressions to compute")
    filters: dict[str, Any] = Field(default_factory=dict, description="Active filter context e.g. {'region': 'North', 'amount': {'>=': 100}}")
    limit: int | None = Field(default=1000, description="Max rows to return")


class SemanticQueryResponse(BaseModel):
    """Response containing semantic query results and generated SQL."""

    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    generated_sql: str = Field("")
    row_count: int = Field(0)
