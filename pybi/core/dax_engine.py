import re
from typing import Any, Dict, List, Optional
from pybi.models.dax import (
    CompletionItem,
    DAXValidationError,
    DAXValidationResponse,
)

# Re-export backend DaxEngine for compatibility
from backend.core.dax_engine import DaxEngine as BackendDaxEngine

DAX_KEYWORDS = ["VAR", "RETURN", "EVALUATE", "DEFINE", "MEASURE", "TRUE", "FALSE", "BLANK"]

DAX_FUNCTIONS = {
    "SUM": {"category": "Aggregation", "syntax": "SUM(<column>)", "doc": "Calcola la somma di tutti i numeri in una colonna."},
    "SUMX": {"category": "Aggregation", "syntax": "SUMX(<table>, <expression>)", "doc": "Calcola la somma di un'espressione valutata per ogni riga di una tabella."},
    "AVERAGE": {"category": "Aggregation", "syntax": "AVERAGE(<column>)", "doc": "Restituisce la media aritmetica dei valori in una colonna."},
    "CALCULATE": {"category": "Filter", "syntax": "CALCULATE(<expression>[, <filter1> [, <filter2> ...]])", "doc": "Valuta un'espressione in un contesto di filtro modificato."},
    "FILTER": {"category": "Filter", "syntax": "FILTER(<table>, <filter>)", "doc": "Restituisce una tabella con le righe filtrate in base alla condizione."},
    "ALL": {"category": "Filter", "syntax": "ALL([<table>|<column>])", "doc": "Rimuove tutti i filtri dalla tabella o dalle colonne specificate."},
    "DATESYTD": {"category": "Time Intelligence", "syntax": "DATESYTD(<dates>[, <year_end_date>])", "doc": "Restituisce una tabella di date dall'inizio dell'anno fino alla data corrente."},
    "SAMEPERIODLASTYEAR": {"category": "Time Intelligence", "syntax": "SAMEPERIODLASTYEAR(<dates>)", "doc": "Restituisce una tabella di date traslate indietro di un anno."},
    "COUNTROWS": {"category": "Aggregation", "syntax": "COUNTROWS([<table>])", "doc": "Conta il numero di righe in una tabella."},
    "DIVIDE": {"category": "Math & Trig", "syntax": "DIVIDE(<numerator>, <denominator>[, <alternateresult>])", "doc": "Esegue una divisione sicura e gestisce la divisione per zero."}
}


class DAXEngine:
    def __init__(self, semantic_model: Optional[Dict[str, Any]] = None):
        self.semantic_model = semantic_model or {}

    def validate_expression(self, expression: str) -> DAXValidationResponse:
        errors: List[DAXValidationError] = []
        if not expression or not expression.strip():
            errors.append(DAXValidationError(line=1, column=1, end_column=1, message="La formula non può essere vuota."))
            return DAXValidationResponse(is_valid=False, errors=errors)

        # Parse measure name and body
        if "=" in expression:
            parts = expression.split("=", 1)
            measure_name = parts[0].strip()
            body = parts[1].strip()
        else:
            measure_name = "New Measure"
            body = expression.strip()

        # Check balanced parentheses
        open_parens = body.count("(")
        close_parens = body.count(")")
        if open_parens != close_parens:
            errors.append(DAXValidationError(
                line=1,
                column=len(expression),
                end_column=len(expression) + 1,
                message=f"Parentesi non bilanciate: {open_parens} aperte vs {close_parens} chiuse."
            ))

        # Extract references
        ref_tables = list(set(re.findall(r"'([^']+)'", body)))
        ref_columns = list(set(re.findall(r"\[([^\]]+)\]", body)))

        is_valid = len(errors) == 0
        return DAXValidationResponse(
            is_valid=is_valid,
            measure_name=measure_name,
            clean_expression=body,
            errors=errors,
            referenced_tables=ref_tables,
            referenced_columns=ref_columns
        )

    def get_autocomplete_suggestions(self, prefix: str) -> List[CompletionItem]:
        items: List[CompletionItem] = []
        prefix_upper = prefix.upper() if prefix else ""

        # DAX Function suggestions
        for func_name, info in DAX_FUNCTIONS.items():
            if not prefix_upper or func_name.startswith(prefix_upper):
                items.append(CompletionItem(
                    label=func_name,
                    kind="Function",
                    detail=info["syntax"],
                    documentation=info["doc"],
                    insert_text=f"{func_name}("
                ))

        # Table suggestions from Semantic Model
        tables = self.semantic_model.get("tables", []) if isinstance(self.semantic_model, dict) else []
        for table in tables:
            t_name = table.get("name") if isinstance(table, dict) else getattr(table, "name", str(table))
            if t_name and (not prefix_upper or t_name.upper().startswith(prefix_upper)):
                items.append(CompletionItem(
                    label=f"'{t_name}'",
                    kind="Table",
                    detail="Tabella Modello",
                    documentation=f"Tabella semantica '{t_name}'",
                    insert_text=f"'{t_name}'"
                ))

        return items
