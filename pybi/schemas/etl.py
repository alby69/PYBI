"""Pydantic schemas for Power Query Editor ETL pipeline execution and preview requests."""

from typing import Any, Dict, List, Optional
from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class ETLStep(BaseModel):
    """Linear ETL step representation for Applied Steps panel."""

    model_config = ConfigDict(populate_by_name=True)

    step_id: str = Field(
        default="",
        validation_alias=AliasChoices("step_id", "id"),
        description="ID univoco del passaggio (es. step_1, step_2)",
    )
    step_type: str = Field(
        default="",
        validation_alias=AliasChoices("step_type", "operation", "type"),
        description="Tipo di trasformazione: filter, rename, custom_column, split, merge, group_by",
    )
    name: Optional[str] = Field(
        default=None,
        description="Nome visualizzato nel pannello Applied Steps",
    )
    description: Optional[str] = Field(
        default=None,
        description="Descrizione opzionale del passaggio",
    )
    params: Dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("params", "parameters", "config"),
        description="Parametri specifici della trasformazione",
    )

    def model_post_init(self, __context: Any) -> None:
        if not self.name:
            self.name = self.step_type or self.step_id or "step"

    @property
    def id(self) -> str:
        return self.step_id

    @property
    def operation(self) -> str:
        return self.step_type

    @property
    def parameters(self) -> Dict[str, Any]:
        return self.params


class ETLQuery(BaseModel):
    """Linear ETL Query representation containing source definition and sequential steps."""

    model_config = ConfigDict(populate_by_name=True)

    query_name: str = Field(
        default="Sales_Data",
        validation_alias=AliasChoices("query_name", "name"),
        description="Nome della tabella/query corrente",
    )
    source: Dict[str, Any] = Field(
        default_factory=dict,
        description="Configurazione della sorgente dati (file CSV/Parquet, DB table)",
    )
    steps: List[ETLStep] = Field(
        default_factory=list,
        description="Lista ordinata dei passaggi applicati",
    )


class ETLExecuteRequest(BaseModel):
    """Payload for requesting execution of an ETL linear query."""

    query: Optional[ETLQuery] = None
    target_table_name: str = "target_table"


class ETLPreviewRequest(BaseModel):
    """Payload for requesting preview of linear query up to step_index."""

    query: Optional[ETLQuery] = None
    source_table: Optional[str] = None
    steps: List[ETLStep] = Field(default_factory=list)
    step_index: Optional[int] = Field(
        default=None,
        description="Indice del passaggio fino a cui calcolare l'anteprima",
    )
    limit: int = Field(default=1000, description="Limite massimo di righe da restituire")
