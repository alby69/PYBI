from fastapi import APIRouter, HTTPException, Depends
from pybi.models.dax import (
    DAXAutoCompleteRequest,
    DAXAutoCompleteResponse,
    DAXValidationRequest,
    DAXValidationResponse,
    MeasureDefinition,
)
from pybi.core.dax_engine import DAXEngine

router = APIRouter(prefix="/api/v1/projects/{project_id}/dax", tags=["DAX Engine"])


@router.post("/validate", response_model=DAXValidationResponse)
async def validate_dax_formula(project_id: str, payload: DAXValidationRequest):
    semantic_model = {"tables": [{"name": "Sales"}, {"name": "Customer"}, {"name": "Calendar"}]}
    engine = DAXEngine(semantic_model)
    return engine.validate_expression(payload.expression)


@router.post("/autocomplete", response_model=DAXAutoCompleteResponse)
async def autocomplete_dax(project_id: str, payload: DAXAutoCompleteRequest):
    semantic_model = {"tables": [{"name": "Sales"}, {"name": "Customer"}, {"name": "Calendar"}]}
    engine = DAXEngine(semantic_model)

    prefix = payload.expression[:payload.cursor_position].split()[-1] if payload.expression else ""
    prefix = prefix.replace("(", "").replace("[", "").replace("'", "")

    suggestions = engine.get_autocomplete_suggestions(prefix)
    return DAXAutoCompleteResponse(suggestions=suggestions)


@router.post("/measures", response_model=MeasureDefinition)
async def create_or_update_measure(project_id: str, measure: MeasureDefinition):
    return measure
