"""Locale catalogs served to the NiceGUI Vue components."""

from __future__ import annotations

import json
from importlib.resources import files
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/v1/locales", tags=["Internationalization"])


@router.get("/{locale}", response_model=Dict[str, Any])
async def get_locale_catalog(locale: str) -> Dict[str, Any]:
    """Load a supported locale catalog from package resources."""
    locale = locale.lower()
    if locale not in {"it", "en"}:
        raise HTTPException(status_code=404, detail="Locale not found")
    catalog = files("pybi.ui").joinpath("locales", f"{locale}.json")
    return json.loads(catalog.read_text(encoding="utf-8"))