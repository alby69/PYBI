from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TableFilterRule(BaseModel):
    table_name: str = Field(..., description="Nome della tabella target nel modello semantico")
    filter_expression: str = Field(..., description="Espressione DAX/SQL di filtro (es. [Country] = 'Italy' o [Region] = USERNAME())")
    is_active: bool = True


class SecurityRole(BaseModel):
    role_id: str = Field(..., description="Identificativo univoco del ruolo")
    role_name: str = Field(..., description="Nome visualizzato del ruolo (es. 'Manager Europa')")
    description: Optional[str] = None
    table_filters: List[TableFilterRule] = Field(default_factory=list, description="Elenco delle regole di filtro per tabella")


class UserRoleMapping(BaseModel):
    user_id: str = Field(..., description="ID utente, email o username")
    roles: List[str] = Field(..., description="Lista di role_id assegnati all'utente")
    custom_attributes: Dict[str, Any] = Field(default_factory=dict, description="Attributi dinamici utente (es. {'Region': 'EMEA'})")


class RLSUserContext(BaseModel):
    user_id: str
    username: str
    effective_roles: List[str] = Field(default_factory=list)
    custom_attributes: Dict[str, Any] = Field(default_factory=dict)
    is_simulated: bool = False
