"""Core Pydantic data models for PyBI."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DataType(str, Enum):
    """Supported data types in PyBI Semantic Model."""

    INTEGER = "INTEGER"
    FLOAT = "FLOAT"
    STRING = "STRING"
    BOOLEAN = "BOOLEAN"
    DATE = "DATE"
    DATETIME = "DATETIME"
    UNKNOWN = "UNKNOWN"


class ColumnMeta(BaseModel):
    """Metadata for a semantic model column."""

    name: str
    data_type: DataType = DataType.UNKNOWN
    is_key: bool = False
    is_hidden: bool = False
    description: str | None = None


class RelationshipType(str, Enum):
    """Relationship cardinality."""

    ONE_TO_MANY = "1:*"
    MANY_TO_ONE = "*:1"
    ONE_TO_ONE = "1:1"
    MANY_TO_MANY = "*:*"


class Relationship(BaseModel):
    """Relationship between two semantic tables."""

    from_table: str
    from_column: str
    to_table: str
    to_column: str
    cardinality: RelationshipType = RelationshipType.MANY_TO_ONE


class TableSchema(BaseModel):
    """Schema definition for a semantic table."""

    name: str
    columns: list[ColumnMeta] = Field(default_factory=list)
    primary_key: list[str] | None = None
    source_node_id: str | None = None


class ETLDAG(BaseModel):
    """Data representation of an ETL Directed Acyclic Graph."""

    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)


class DashboardLayout(BaseModel):
    """Dashboard layout configuration containing grid items and widgets."""

    widgets: list[dict[str, Any]] = Field(default_factory=list)
    grid_layout: list[dict[str, Any]] = Field(default_factory=list)


class Project(BaseModel):
    """PyBI Project model encapsulating ETL DAG, Dashboard layout, and Data Model."""

    id: str
    name: str
    description: str | None = None
    dag: ETLDAG = Field(default_factory=ETLDAG)
    dashboard: DashboardLayout = Field(default_factory=DashboardLayout)
    relationships: list[Relationship] = Field(default_factory=list)
