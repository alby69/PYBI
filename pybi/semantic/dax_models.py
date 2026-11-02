from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DAXFunctionCategory(str, Enum):
    AGGREGATION = "Aggregation"
    FILTER = "Filter"
    DATE_TIME = "Date & Time"
    TIME_INTELLIGENCE = "Time Intelligence"
    LOGICAL = "Logical"
    MATH = "Math & Trig"
    TEXT = "Text"
    STATISTICAL = "Statistical"


class MeasureDefinition(BaseModel):
    id: str = Field(..., description="ID unico della misura")
    name: str = Field(..., description="Nome della misura (es. 'Total Sales')")
    table_name: str = Field(..., description="Tabella del modello semantico a cui appartiene")
    expression: str = Field(..., description="Formula DAX (es. 'Total Sales = SUM(Sales[Amount])')")
    format_string: str = Field(default="#,##0.00 €", description="Stringa di formattazione visiva")
    display_folder: Optional[str] = Field(default=None, description="Cartella di organizzazione visiva")
    description: Optional[str] = Field(default=None, description="Documentazione o descrizione della misura")
    is_hidden: bool = Field(default=False, description="Nascondi la misura nei report")
    dependencies: List[str] = Field(default_factory=list, description="Lista di colonne e altre misure usate")


class DAXValidationError(BaseModel):
    line: int
    column: int
    end_column: int
    message: str
    severity: str = "Error"  # Error, Warning


class DAXValidationRequest(BaseModel):
    expression: str
    current_table: Optional[str] = None
    project_id: Optional[str] = None


class DAXValidationResponse(BaseModel):
    is_valid: bool
    measure_name: Optional[str] = None
    clean_expression: Optional[str] = None
    errors: List[DAXValidationError] = Field(default_factory=list)
    referenced_tables: List[str] = Field(default_factory=list)
    referenced_columns: List[str] = Field(default_factory=list)
    referenced_measures: List[str] = Field(default_factory=list)


class CompletionItem(BaseModel):
    label: str
    kind: str  # Function, Table, Column, Measure, Keyword
    detail: str
    documentation: str
    insert_text: str


class DAXAutoCompleteRequest(BaseModel):
    expression: str
    cursor_position: int
    project_id: Optional[str] = None


class DAXAutoCompleteResponse(BaseModel):
    suggestions: List[CompletionItem] = Field(default_factory=list)
