"""Dynamic Row-Level Security (RLS) Engine for PyBI."""

import logging
from typing import Any

from pybi.auth.jwt_auth import AuthUser
from pybi.core.semantic_model import CoreSemanticModel

log = logging.getLogger(__name__)


class RLSEngine:
    """Evaluates RLS rules defined in a SemanticModel against user JWT claims and generates SQL WHERE clauses."""

    @staticmethod
    def sanitize_val(val: Any) -> str:
        """Sanitize values for safe SQL injection avoidance."""
        if isinstance(val, (int, float)):
            return str(val)
        val_str = str(val).replace("'", "''")
        return f"'{val_str}'"

    @classmethod
    def get_rls_clauses(cls, model: CoreSemanticModel, user: AuthUser) -> list[str]:
        """Evaluate RLS rules for the model against user claims.

        Args:
            model: Semantic model containing rls_rules.
            user: Authenticated user containing claims.

        Returns:
            List[str]: List of SQL WHERE clause filter strings.
        """
        if not model or not model.rls_rules:
            return []

        clauses: list[str] = []

        for rule in model.rls_rules:
            tbl_name = rule.target_table
            expr_template = rule.filter_expression

            # Check if rule references user claims or properties
            context: dict = {
                "user_id": user.username,
                "role": user.role,
                "email": user.email or "",
            }
            context.update(user.claims)

            # Look for placeholders in expression template, e.g. region = '{allowed_regions}'
            substitutions = {}
            skip_rule = False

            for key, val in context.items():
                placeholder = f"{{{key}}}"
                if placeholder in expr_template:
                    if val == "*" or val == ["*"]:
                        # Full access wildcard
                        skip_rule = True
                        break
                    elif isinstance(val, (list, tuple)):
                        sanitized_vals = ", ".join(cls.sanitize_val(v) for v in val)
                        # Replace = '{key}' with IN (...)
                        eq_placeholder = f"= '{placeholder}'"
                        if eq_placeholder in expr_template:
                            expr_template = expr_template.replace(eq_placeholder, f"IN ({sanitized_vals})")
                        else:
                            substitutions[key] = f"({sanitized_vals})"
                    else:
                        substitutions[key] = cls.sanitize_val(val) if not isinstance(val, (int, float)) else str(val)

            if skip_rule:
                continue

            # Format template if placeholders remain
            try:
                # Direct string replace for clean quotes handling
                formatted_expr = expr_template
                for k, v in substitutions.items():
                    # Handle quoted placeholder vs raw
                    formatted_expr = formatted_expr.replace(f"'{'{'}{k}{'}'}'", v)
                    formatted_expr = formatted_expr.replace(f"{{{k}}}", v)

                # Qualify with target table name if not qualified
                if not ("." in formatted_expr):
                    clause = f'"{tbl_name}".{formatted_expr}'
                else:
                    clause = formatted_expr

                clauses.append(clause)
            except Exception as e:
                log.warning(f"Error compiling RLS rule '{rule.name}': {e}")

        return clauses
