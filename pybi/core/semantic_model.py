"""Core Semantic Model specification for PyBI (Tables, Columns, Measures, Relationships, RLS, and YAML serialization)."""

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import yaml
from pydantic import BaseModel, Field


class Cardinality(str, Enum):
    """Relationship cardinality."""

    ONE_TO_ONE = "1:1"
    ONE_TO_MANY = "1:*"
    MANY_TO_ONE = "*:1"
    MANY_TO_MANY = "*:*"


class JoinType(str, Enum):
    """SQL Join Type."""

    LEFT = "LEFT"
    INNER = "INNER"
    RIGHT = "RIGHT"
    FULL = "FULL"


class SemanticColumn(BaseModel):
    """Column definition within a semantic table."""

    name: str = Field(..., description="Unique dimension or column identifier")
    column_name: str = Field(..., description="Physical database column name")
    data_type: str = Field("string", description="Data type e.g. string, integer, float, date")
    label: Optional[str] = Field(None, description="Human readable display label")
    is_key: bool = Field(False, description="Whether column is a key column")
    is_hidden: bool = Field(False, description="Whether column is hidden from visualization picker")
    hierarchy: Optional[List[str]] = Field(None, description="Hierarchy drill-down path")


class SemanticMeasure(BaseModel):
    """Measure definition within a semantic model."""

    name: str = Field(..., description="Unique measure identifier")
    expression: Optional[str] = Field(None, description="Aggregation or formula expression e.g. SUM(amount)")
    agg_func: Optional[str] = Field("SUM", description="Aggregation function: SUM, AVG, COUNT, MIN, MAX")
    column_name: Optional[str] = Field(None, description="Physical target column for simple aggregations")
    format_string: Optional[str] = Field(None, description="Formatting template e.g. '${:,.2f}'")
    label: Optional[str] = Field(None, description="Human readable display label")


class SemanticRelationship(BaseModel):
    """Relationship between two semantic tables."""

    from_table: str = Field(..., description="Source table name")
    from_column: str = Field(..., description="Source column key")
    to_table: str = Field(..., description="Target table name")
    to_column: str = Field(..., description="Target column key")
    cardinality: Union[Cardinality, str] = Field(Cardinality.MANY_TO_ONE, description="Relationship cardinality")
    join_type: Union[JoinType, str] = Field(JoinType.LEFT, description="Join type: LEFT, INNER, etc.")
    is_active: bool = Field(True, description="Whether relationship is active")


class RLSRule(BaseModel):
    """Row-Level Security rule definition."""

    name: str = Field(..., description="Rule name")
    target_table: str = Field(..., description="Target table name")
    filter_expression: str = Field(..., description="Filter expression template e.g. region = '{user_allowed_region}'")


class SemanticTable(BaseModel):
    """Semantic table definition containing columns and measures."""

    name: str = Field(..., description="Semantic table name")
    source_table: str = Field(..., description="Physical table or DuckDB view name")
    columns: List[SemanticColumn] = Field(default_factory=list, description="Defined columns/dimensions")
    measures: List[SemanticMeasure] = Field(default_factory=list, description="Defined calculated measures")
    primary_key: Optional[List[str]] = Field(None, description="Primary key columns")


class SemanticModel(BaseModel):
    """Root Semantic Model encapsulating tables, relationships, and RLS rules."""

    name: str = Field(..., description="Semantic model identifier")
    tables: List[SemanticTable] = Field(default_factory=list, description="Tables in model")
    relationships: List[SemanticRelationship] = Field(default_factory=list, description="Table relationships")
    rls_rules: List[RLSRule] = Field(default_factory=list, description="Row-level security rules")
    default_table: Optional[str] = Field(None, description="Default source table name")

    def get_table(self, table_name: str) -> Optional[SemanticTable]:
        """Retrieve table by name."""
        for t in self.tables:
            if t.name == table_name:
                return t
        return None

    def find_column(self, col_or_dim_name: str) -> Optional[tuple[SemanticTable, SemanticColumn]]:
        """Find a column or dimension by name or table.col_name syntax."""
        if "." in col_or_dim_name:
            t_name, c_name = col_or_dim_name.split(".", 1)
            tbl = self.get_table(t_name)
            if tbl:
                for c in tbl.columns:
                    if c.name == c_name or c.column_name == c_name:
                        return tbl, c
        else:
            for tbl in self.tables:
                for c in tbl.columns:
                    if c.name == col_or_dim_name or c.column_name == col_or_dim_name:
                        return tbl, c
        return None

    def find_measure(self, meas_name: str) -> Optional[tuple[SemanticTable, SemanticMeasure]]:
        """Find a measure by name or table.meas_name syntax."""
        if "." in meas_name:
            t_name, m_name = meas_name.split(".", 1)
            tbl = self.get_table(t_name)
            if tbl:
                for m in tbl.measures:
                    if m.name == m_name:
                        return tbl, m
        else:
            for tbl in self.tables:
                for m in tbl.measures:
                    if m.name == meas_name:
                        return tbl, m
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Export model as dictionary."""
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SemanticModel":
        """Instantiate model from dictionary."""
        return cls.model_validate(data)

    def to_yaml(self) -> str:
        """Export model to YAML string."""
        data = self.to_dict()
        return yaml.dump(data, sort_keys=False, default_flow_style=False)

    @classmethod
    def from_yaml(cls, yaml_content: str) -> "SemanticModel":
        """Parse SemanticModel from YAML string."""
        parsed = yaml.safe_load(yaml_content) or {}
        return cls.from_dict(parsed)

    def save_yaml_file(self, filepath: Union[str, Path]) -> None:
        """Save SemanticModel to YAML file."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_yaml(), encoding="utf-8")

    @classmethod
    def load_yaml_file(cls, filepath: Union[str, Path]) -> "SemanticModel":
        """Load SemanticModel from YAML file."""
        content = Path(filepath).read_text(encoding="utf-8")
        return cls.from_yaml(content)


def autodetect_relationships(
    tables: List[SemanticTable],
    existing_relationships: Optional[List[SemanticRelationship]] = None,
) -> List[SemanticRelationship]:
    """Scans tables for matching column names and data types to propose relationships.

    Args:
        tables: List of SemanticTable objects to scan.
        existing_relationships: Existing relationships to avoid duplicating.

    Returns:
        List[SemanticRelationship]: List of newly detected relationships.
    """
    detected: List[SemanticRelationship] = []
    existing_pairs = set()
    if existing_relationships:
        for r in existing_relationships:
            existing_pairs.add((r.from_table, r.from_column, r.to_table, r.to_column))
            existing_pairs.add((r.to_table, r.to_column, r.from_table, r.from_column))

    for i in range(len(tables)):
        for j in range(i + 1, len(tables)):
            tbl1 = tables[i]
            tbl2 = tables[j]
            for c1 in tbl1.columns:
                for c2 in tbl2.columns:
                    # Match by column name and data type
                    if c1.name.lower() == c2.name.lower() and c1.data_type.lower() == c2.data_type.lower():
                        pair1 = (tbl1.name, c1.name, tbl2.name, c2.name)
                        pair2 = (tbl2.name, c2.name, tbl1.name, c1.name)
                        if pair1 in existing_pairs or pair2 in existing_pairs:
                            continue

                        # Determine default cardinality: if target is key/unique, MANY_TO_ONE (*:1)
                        if c2.is_key and not c1.is_key:
                            from_t, from_c = tbl1.name, c1.name
                            to_t, to_c = tbl2.name, c2.name
                            card = Cardinality.MANY_TO_ONE
                        elif c1.is_key and not c2.is_key:
                            from_t, from_c = tbl2.name, c2.name
                            to_t, to_c = tbl1.name, c1.name
                            card = Cardinality.MANY_TO_ONE
                        elif c1.is_key and c2.is_key:
                            from_t, from_c = tbl1.name, c1.name
                            to_t, to_c = tbl2.name, c2.name
                            card = Cardinality.ONE_TO_ONE
                        else:
                            from_t, from_c = tbl1.name, c1.name
                            to_t, to_c = tbl2.name, c2.name
                            card = Cardinality.MANY_TO_ONE

                        rel = SemanticRelationship(
                            from_table=from_t,
                            from_column=from_c,
                            to_table=to_t,
                            to_column=to_c,
                            cardinality=card,
                            join_type=JoinType.LEFT,
                            is_active=True,
                        )
                        detected.append(rel)
                        existing_pairs.add(pair1)
                        existing_pairs.add(pair2)

    return detected


CoreSemanticModel = SemanticModel
