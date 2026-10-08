"""Semantic Layer models for PyBI (Dimensions, Measures, SemanticModel, and Queries)."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Dimension(BaseModel):
    """Semantic dimension representing a categorical or temporal column."""

    name: str = Field(..., description="Unique dimension identifier or column name")
    column_name: str = Field(..., description="Database column name")
    data_type: str = Field("string", description="Data type: string, integer, float, date, datetime, etc.")
    hierarchy: Optional[List[str]] = Field(default=None, description="Drill-down hierarchy (e.g., ['year', 'quarter', 'month'])")
    label: Optional[str] = Field(default=None, description="Human readable label")


class Measure(BaseModel):
    """Semantic measure representing a numeric aggregation or formula."""

    name: str = Field(..., description="Unique measure identifier")
    expression: Optional[str] = Field(default=None, description="Aggregation expression e.g. SUM(amount), AVG(price), or formula")
    agg_func: Optional[str] = Field(default="SUM", description="Aggregation function: SUM, AVG, COUNT, MIN, MAX, CUSTOM")
    column_name: Optional[str] = Field(default=None, description="Target column name for basic aggregations")
    format_string: Optional[str] = Field(default=None, description="Formatting template e.g. '${:,.2f}' or '{:,.0f}'")
    label: Optional[str] = Field(default=None, description="Human readable label")


class SemanticModel(BaseModel):
    """Semantic model bundling table source, dimensions, and measures."""

    name: str = Field(..., description="Name of the semantic model")
    source_table: str = Field(..., description="Source table or view name in DuckDB/binder")
    dimensions: List[Dimension] = Field(default_factory=list, description="Defined dimensions")
    measures: List[Measure] = Field(default_factory=list, description="Defined measures")


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
