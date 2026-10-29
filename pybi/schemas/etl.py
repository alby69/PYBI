"""Pydantic schemas for Power Query Editor ETL pipeline execution and preview requests."""

from typing import Any, Dict, List, Optional
from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class ETLStep(BaseModel):
    """Linear ETL step representation for Applied Steps panel."""

    model_config = ConfigDict(populate_by_name=True)

    step_id: str = Field(
        ...,
        validation_alias=AliasChoices("step_id", "id"),
        description="ID univoco del passaggio (es. step_1, step_2)",
    )
    step_type: str = Field(
        ...,
        validation_alias=AliasChoices("step_type", "operation", "type"),
        description="Tipo di trasformazione: filter, rename, custom_column, split, merge, group_by",
    )
    name: str = Field(..., description="Nome visualizzato nel pannello Applied Steps")
    description: Optional[str] = Field(default=None, description="Descrizione opzionale del passaggio")
    params: Dict[str, Any] = Field(
        default_factory=dict, description="Parametri specifici della trasformazione"
    )

    @property
    def id(self) -> str:
        return self.step_id

    @property
    def operation(self) -> str:
        return self.step_type


class ETLQuery(BaseModel):
    """Linear ETL Query representation containing source definition and sequential steps."""

    query_name: str = Field(..., description="Nome della tabella/query corrente")
    source: Dict[str, Any] = Field(
        ..., description="Configurazione della sorgente dati (file CSV/Parquet, DB table)"
    )
    steps: List[ETLStep] = Field(
        default_factory=list, description="Lista ordinata dei passaggi applicati"
    )


class ETLExecuteRequest(BaseModel):
    """Payload for requesting execution of an ETL linear query."""

    query: ETLQuery
    target_table_name: str


class ETLPreviewRequest(BaseModel):
    """Payload for requesting preview of linear query up to step_index."""

    query: ETLQuery
    step_index: int = Field(..., description="Indice del passaggio fino a cui calcolare l'anteprima")
