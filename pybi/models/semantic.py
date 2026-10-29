"""Semantic model specification for Model View and Relationship Editor in PYBI."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


class CardinalityType(str, Enum):
    """Relationship cardinality type."""

    ONE_TO_ONE = "1:1"
    ONE_TO_MANY = "1:*"
    MANY_TO_ONE = "*:1"
    MANY_TO_MANY = "*:*"


class CrossFilterDirection(str, Enum):
    """Cross-filter direction between related tables."""

    SINGLE = "single"  # Filter direction from dimension to fact (1 -> *)
    BOTH = "both"      # Bidirectional cross filtering (* <-> *)


class JoinType(str, Enum):
    """SQL Join Type."""

    INNER = "INNER"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    FULL = "FULL"


class Relationship(BaseModel):
    """Relationship definition between two model tables."""

    id: Optional[str] = Field(None, description="ID univoco relazione, es. rel_orders_customers")
    from_table: str = Field(..., description="Nome tabella origine (es. FactOrders)")
    from_column: str = Field(..., description="Nome colonna origine (es. CustomerID)")
    to_table: str = Field(..., description="Nome tabella destinazione (es. DimCustomer)")
    to_column: str = Field(..., description="Nome colonna destinazione (es. CustomerID)")
    cardinality: CardinalityType = CardinalityType.MANY_TO_ONE
    cross_filter_direction: CrossFilterDirection = CrossFilterDirection.SINGLE
    join_type: JoinType = JoinType.LEFT
    is_active: bool = True
    description: Optional[str] = None

    @model_validator(mode="after")
    def ensure_id(self) -> "Relationship":
        """Auto-generate ID if not specified."""
        if not self.id:
            self.id = f"rel_{self.from_table}_{self.from_column}_{self.to_table}_{self.to_column}".lower()
        return self


class Measure(BaseModel):
    """Calculated measure definition."""

    id: Optional[str] = None
    name: str = Field(..., description="Nome misura, es. 'Totale Vendite'")
    table_name: str = Field(..., description="Tabella di appartenenza/home table")
    expression: str = Field(..., description="Formula DAX o espressione DuckDB SQL, es. SUM(FactOrders.SalesAmount)")
    format_string: Optional[str] = "€ #,##0.00"
    display_folder: Optional[str] = None
    description: Optional[str] = None
    is_hidden: bool = False

    @model_validator(mode="after")
    def ensure_id(self) -> "Measure":
        """Auto-generate ID if not specified."""
        if not self.id:
            self.id = f"meas_{self.table_name}_{self.name}".lower()
        return self


class HierarchyLevel(BaseModel):
    """Hierarchy level definition."""

    name: str
    column_name: str


class Hierarchy(BaseModel):
    """Hierarchy definition spanning columns within a table."""

    id: Optional[str] = None
    name: str = Field(..., description="Es. 'Gerarchia Calendario'")
    table_name: str
    levels: List[HierarchyLevel] = Field(default_factory=list)

    @model_validator(mode="after")
    def ensure_id(self) -> "Hierarchy":
        """Auto-generate ID if not specified."""
        if not self.id:
            self.id = f"hier_{self.table_name}_{self.name}".lower()
        return self


class ColumnMetadata(BaseModel):
    """Column metadata definition."""

    name: str
    data_type: str = "string"
    is_key: bool = False
    is_hidden: bool = False
    display_folder: Optional[str] = None
    format_string: Optional[str] = None
    description: Optional[str] = None


class TableMetadata(BaseModel):
    """Table metadata definition."""

    name: str
    is_hidden: bool = False
    display_folder: Optional[str] = None
    position_x: float = 0.0
    position_y: float = 0.0
    columns: List[ColumnMetadata] = Field(default_factory=list)
    measures: List[Measure] = Field(default_factory=list)


class SemanticModel(BaseModel):
    """Semantic model root structure for Model View."""

    project_id: str
    name: Optional[str] = None
    tables: List[TableMetadata] = Field(default_factory=list)
    relationships: List[Relationship] = Field(default_factory=list)
    measures: List[Measure] = Field(default_factory=list)
    hierarchies: List[Hierarchy] = Field(default_factory=list)
