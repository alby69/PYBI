"""FastAPI router for ETL Code Export operations in PyBI."""

from typing import Any, Dict, Union
from fastapi import APIRouter, HTTPException, Response

from pybi.etl.polars_generator import PolarsCodeGenerator
from pybi.schemas.etl import ETLQuery

router = APIRouter(tags=["ETL Code Export"])


@router.post(
    "/api/v1/etl/export/python",
    summary="Esporta la pipeline ETL come script Python Polars",
    response_class=Response,
)
@router.post(
    "/api/v1/projects/{project_id}/etl/export/python",
    summary="Esporta la pipeline ETL per un progetto come script Python Polars",
    response_class=Response,
)
async def export_python_script(
    query: Union[ETLQuery, Dict[str, Any]],
    project_id: str = None,
):
    """
    Transpiles the provided ETLQuery step sequence into a standalone downloadable Python script using Polars.
    """
    try:
        generator = PolarsCodeGenerator(query)
        python_code = generator.generate_python_code()
        filename = f"pipeline_{generator.query_id}.py"

        return Response(
            content=python_code,
            media_type="text/x-python",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Errore nella generazione dello script Python: {str(e)}",
        )
