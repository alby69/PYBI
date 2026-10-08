"""Semantic Data Model schema definitions for PyBI."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DataType(str, Enum):
    """Semantic model data types."""

    INTEGER = "INTEGER"
    FLOAT = "FLOAT"
    STRING = "STRING"
    BOOLEAN = "BOOLEAN"
    DATE = "DATE"
    DATETIME = "DATETIME"
    UNKNOWN = "UNKNOWN"


class Column(BaseModel):
    """Semantic model column metadata."""

    name: str
    data_type: DataType = DataType.UNKNOWN
    is_key: bool = False
    is_hidden: bool = False
    description: Optional[str] = None


class RelationshipCardinality(str, Enum):
    """Relationship cardinality."""

    ONE_TO_MANY = "1:*"
    MANY_TO_ONE = "*:1"
    ONE_TO_ONE = "1:1"
    MANY_TO_MANY = "*:*"


class Relationship(BaseModel):
    """Relationship between two semantic model tables."""

    from_table: str
    from_column: str
    to_table: str
    to_column: str
    cardinality: RelationshipCardinality = RelationshipCardinality.MANY_TO_ONE


class Table(BaseModel):
    """Semantic model table definition."""

    name: str
    columns: List[Column] = Field(default_factory=list)
    primary_key: Optional[List[str]] = None
    source_node_id: Optional[str] = None


class SemanticModel(BaseModel):
    """Complete semantic model schema representing tables and relationships."""

    tables: Dict[str, Table] = Field(default_factory=dict)
    relationships: List[Relationship] = Field(default_factory=list)

    def add_table(self, table: Table) -> None:
        """Add or update a table in the semantic model."""
        self.tables[table.name] = table

    def add_relationship(self, relationship: Relationship) -> None:
        """Add a relationship to the semantic model."""
        self.relationships.append(relationship)
