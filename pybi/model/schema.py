"""Semantic Data Model schema definitions for PyBI."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal


class DataType(str, Enum):
    """Semantic model data types."""

    INTEGER = "INTEGER"
    FLOAT = "FLOAT"
    STRING = "STRING"
    BOOLEAN = "BOOLEAN"
    DATE = "DATE"
    DATETIME = "DATETIME"
    UNKNOWN = "UNKNOWN"


@dataclass
class Column:
    """Semantic model column metadata."""

    name: str
    data_type: str | DataType = DataType.UNKNOWN
    is_hidden: bool = False
    is_key: bool = False
    description: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.data_type, DataType):
            self.data_type = self.data_type.value


class RelationshipCardinality(str, Enum):
    """Relationship cardinality."""

    ONE_TO_MANY = "1:*"
    MANY_TO_ONE = "*:1"
    ONE_TO_ONE = "1:1"
    MANY_TO_MANY = "*:*"


@dataclass
class Relationship:
    """Relationship between two semantic model tables."""

    name: str = ""
    from_table: str = ""
    from_column: str = ""
    to_table: str = ""
    to_column: str = ""
    cross_filter_direction: Literal["Single", "Both"] = "Single"
    cardinality: RelationshipCardinality = RelationshipCardinality.MANY_TO_ONE


@dataclass
class Table:
    """Semantic model table definition."""

    name: str
    columns: list[Column] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    primary_key: list[str] | None = None
    source_node_id: str | None = None


@dataclass
class SemanticModel:
    """Complete semantic model schema representing tables and relationships."""

    tables: dict[str, Table] = field(default_factory=dict)
    relationships: list[Relationship] = field(default_factory=list)

    def add_table(self, table: Table) -> None:
        """Add or update a table in the semantic model."""
        self.tables[table.name] = table

    def add_relationship(self, relationship: Relationship) -> None:
        """Add a relationship to the semantic model."""
        self.relationships.append(relationship)
