"""Language negotiation and localized API error helpers."""

from __future__ import annotations

import re

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware

SUPPORTED_LOCALES = {"en", "it"}


def _locale_code(value: str) -> str:
    return value.split("-", 1)[0].strip().lower()


def negotiate_locale(accept_language: str, cookie_locale: str | None = None) -> str:
    """Choose a supported language, preferring the explicit locale cookie."""
    if cookie_locale:
        locale = _locale_code(cookie_locale)
        if locale in SUPPORTED_LOCALES:
            return locale

    candidates = []
    for index, entry in enumerate(accept_language.split(",")):
        language, *parameters = entry.strip().split(";")
        locale = _locale_code(language)
        quality = 1.0
        for parameter in parameters:
            key, separator, value = parameter.strip().partition("=")
            if separator and key.lower() == "q":
                try:
                    quality = float(value)
                except ValueError:
                    quality = 0
        if locale in SUPPORTED_LOCALES and quality > 0:
            candidates.append((quality, -index, locale))

    if candidates:
        return max(candidates)[2]
    return "it"


class I18nMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.language = negotiate_locale(
            request.headers.get("accept-language", ""),
            request.cookies.get("pybi_locale"),
        )
        response = await call_next(request)
        response.headers["Content-Language"] = request.state.language
        return response


def install_i18n_middleware(app) -> None:
    """Install the locale middleware once on FastAPI or NiceGUI's app."""
    if not any(item.cls is I18nMiddleware for item in app.user_middleware):
        app.add_middleware(I18nMiddleware)


def localize_http_exception(request: Request, exception: HTTPException) -> dict:
    """Preserve API details while translating common framework and project errors."""
    detail = exception.detail
    if not isinstance(detail, str):
        return {"detail": detail, "code": "API_ERROR"}

    if request.state.language == "it":
        if detail == "Not Found":
            detail = "Risorsa non trovata"
        elif detail == "Method Not Allowed":
            detail = "Metodo non consentito"
        else:
            project_match = re.fullmatch(r"Project '(.+)' not found", detail)
            table_match = re.fullmatch(r"Table '(.+)' not found in project '(.+)'", detail)
            if project_match:
                detail = f"Progetto '{project_match.group(1)}' non trovato"
            elif table_match:
                detail = f"Tabella '{table_match.group(1)}' non trovata nel progetto '{table_match.group(2)}'"

    return {"detail": detail, "code": "API_ERROR"}


def localized_validation_response(request: Request, exception: RequestValidationError) -> dict:
    """Return validation errors with localized, stable messages and field paths."""
    language = request.state.language
    errors = []
    for error in exception.errors():
        message = error.get("msg", "Invalid value")
        if language == "it":
            if message.lower() in {"field required", "missing"}:
                message = "Campo obbligatorio"
            elif message.lower().startswith("input should be a valid integer"):
                message = "Il valore deve essere un numero intero valido"
            elif message.lower().startswith("input should be a valid number"):
                message = "Il valore deve essere numerico"
            elif message.lower().startswith("input should be a valid string"):
                message = "Il valore deve essere un testo"
        errors.append({
            "loc": list(error.get("loc", ())),
            "msg": message,
            "type": error.get("type", "value_error"),
        })
    return {
        "detail": errors,
        "code": "VALIDATION_ERROR",
    }