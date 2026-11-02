"""Compatibility exports for the historical backend API v1 models."""

from typing import Any, Dict, List, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from pybi.api.v1.models import *
from pybi.api.v1.models import ETLEdgeSchema, ETLNodeSchema


class ETLStep(BaseModel):
    """Linear ETL step using the historical ``id`` and ``operation`` fields."""

    model_config = ConfigDict(populate_by_name=True)

    id: Optional[str] = Field(
        default="",
        validation_alias=AliasChoices("id", "step_id"),
        description="Unique step identifier",
    )
    name: Optional[str] = Field(default=None, description="Display step name")
    operation: Optional[str] = Field(
        default="",
        validation_alias=AliasChoices("operation", "step_type", "type"),
        description="Operation type",
    )
    params: Dict[str, Any] = Field(default_factory=dict)


class ETLQuery(BaseModel):
    """Historical linear ETL query representation."""

    query_name: str = "Sales_Data"
    source: Dict[str, Any] = Field(default_factory=dict)
    steps: List[ETLStep] = Field(default_factory=list)


class ETLDAGSchema(BaseModel):
    """Historical ETL DAG representation."""

    nodes: List[ETLNodeSchema] = Field(default_factory=list)
    edges: List[ETLEdgeSchema] = Field(default_factory=list)
    query_name: Optional[str] = None
    source: Optional[Dict[str, Any]] = Field(default_factory=dict)
    steps: Optional[List[ETLStep]] = Field(default_factory=list)


class SaveETLDAGRequest(BaseModel):
    """Historical payload for saving an ETL DAG or linear query."""

    dag: Optional[ETLDAGSchema] = None
    query: Optional[ETLQuery] = None


class ETLExecuteRequest(BaseModel):
    """Historical payload for executing an ETL pipeline."""

    project_id: Optional[str] = None
    dag: Optional[ETLDAGSchema] = None
    query: Optional[ETLQuery] = None


class ETLExecuteResponse(BaseModel):
    """Historical ETL execution response."""

    status: str
    logs: List[str] = Field(default_factory=list)
    output_tables: List[str] = Field(default_factory=list)
    error: Optional[str] = None


class ETLPreviewRequest(BaseModel):
    """Historical payload for previewing a node or linear ETL step."""

    project_id: Optional[str] = None
    node_id: Optional[str] = None
    step_index: Optional[int] = None
    limit: int = 1000
    source_table: Optional[str] = None
    steps: List[Any] = Field(default_factory=list)
    query: Optional[ETLQuery] = None


class ETLPreviewResponse(BaseModel):
    """Historical ETL preview response."""

    node_id: Optional[str] = None
    step_index: Optional[int] = None
    columns: List[str] = Field(default_factory=list)
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    total_rows: int
