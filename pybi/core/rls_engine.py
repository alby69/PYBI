"""Dynamic Row-Level Security (RLS) Engine for PyBI.

Parses JWT claims or Security Role definitions and injects sanitized WHERE clause filters
or CTEs into DuckDB SQL queries or SemanticModel queries.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Union

import sqlglot
from sqlglot import parse_one, exp

from pybi.models.security import RLSUserContext, SecurityRole, TableFilterRule

log = logging.getLogger(__name__)


def apply_rls_filters(query: str, jwt_claims: Dict[str, Any], target_table: Optional[str] = None) -> str:
    """Inject dynamic WHERE clauses into standard SQL query based on JWT claims."""
    if not query or not jwt_claims:
        return query

    rls_clauses: List[str] = []

    # Claim: allowed_regions -> WHERE region IN ('IT', 'FR')
    if "allowed_regions" in jwt_claims:
        regions = jwt_claims["allowed_regions"]
        if isinstance(regions, (list, tuple, set)) and regions:
            formatted_regions = ", ".join(f"'{r}'" for r in regions)
            table_prefix = f'"{target_table}".' if target_table else ""
            rls_clauses.append(f"{table_prefix}region IN ({formatted_regions})")

    # Claim: region -> WHERE region = 'EU'
    elif "region" in jwt_claims and jwt_claims["region"]:
        reg = jwt_claims["region"]
        table_prefix = f'"{target_table}".' if target_table else ""
        rls_clauses.append(f"{table_prefix}region = '{reg}'")

    # Claim: allowed_departments -> WHERE department IN (...)
    if "allowed_departments" in jwt_claims:
        depts = jwt_claims["allowed_departments"]
        if isinstance(depts, (list, tuple, set)) and depts:
            formatted_depts = ", ".join(f"'{d}'" for d in depts)
            table_prefix = f'"{target_table}".' if target_table else ""
            rls_clauses.append(f"{table_prefix}department IN ({formatted_depts})")

    # Claim: user_id -> WHERE user_id = '...' (if strict user isolation requested)
    if jwt_claims.get("isolate_user") and "user_id" in jwt_claims:
        uid = jwt_claims["user_id"]
        table_prefix = f'"{target_table}".' if target_table else ""
        rls_clauses.append(f"{table_prefix}user_id = '{uid}'")

    if not rls_clauses:
        return query

    combined_rls_where = " AND ".join(rls_clauses)

    try:
        expression = parse_one(query, read="duckdb")
        if isinstance(expression, exp.Select):
            where = expression.args.get("where")
            if where:
                existing_where = where.this.sql(dialect="duckdb")
                new_where_sql = f"({existing_where}) AND ({combined_rls_where})"
            else:
                new_where_sql = combined_rls_where

            new_where_expr = parse_one(f"SELECT * FROM t WHERE {new_where_sql}", read="duckdb").args.get("where")
            expression.set("where", new_where_expr)
            return expression.sql(dialect="duckdb")
    except Exception as e:
        log.warning(f"SQLGlot AST injection failed ({e}), falling back to regex/string insertion.")

    # Fallback string insertion
    if re.search(r"\bWHERE\b", query, re.IGNORECASE):
        return re.sub(
            r"(\bWHERE\b\s+)",
            rf"\1({combined_rls_where}) AND ",
            query,
            count=1,
            flags=re.IGNORECASE,
        )
    else:
        match = re.search(r"\b(GROUP\s+BY|ORDER\s+BY|LIMIT)\b", query, re.IGNORECASE)
        if match:
            idx = match.start()
            return f"{query[:idx]}WHERE {combined_rls_where} {query[idx:]}"
        else:
            return f"{query} WHERE {combined_rls_where}"


class RLSEngine:
    """Dynamic RLS Engine evaluating user claims or Security Roles against semantic models."""

    def __init__(
        self,
        semantic_model: Optional[Any] = None,
        roles: Optional[List[SecurityRole]] = None,
        default_rules: Optional[List[Dict[str, Any]]] = None,
    ):
        self.semantic_model = semantic_model
        self.roles_map: Dict[str, SecurityRole] = {r.role_id: r for r in (roles or [])}
        self.default_rules = default_rules or []

    def resolve_user_predicates(self, context: RLSUserContext) -> Dict[str, str]:
        table_predicates: Dict[str, List[str]] = {}

        for role_id in context.effective_roles:
            role = self.roles_map.get(role_id)
            if not role:
                continue
            for rule in role.table_filters:
                if not rule.is_active:
                    continue
                sql_predicate = self._translate_expression(rule.filter_expression, context)
                if sql_predicate:
                    table_predicates.setdefault(rule.table_name, []).append(sql_predicate)

        final_predicates: Dict[str, str] = {}
        for table_name, predicates in table_predicates.items():
            if len(predicates) == 1:
                final_predicates[table_name] = predicates[0]
            else:
                combined = " OR ".join([f"({p})" for p in predicates])
                final_predicates[table_name] = f"({combined})"

        return final_predicates

    def _translate_expression(self, expr: str, context: RLSUserContext) -> str:
        sql_expr = expr

        sql_expr = re.sub(r"USERNAME\(\)", f"'{context.username}'", sql_expr, flags=re.IGNORECASE)
        sql_expr = re.sub(r"USERPRINCIPALNAME\(\)", f"'{context.username}'", sql_expr, flags=re.IGNORECASE)

        def attr_replacer(match):
            attr_name = match.group(1)
            val = context.custom_attributes.get(attr_name, "")
            return f"'{val}'"

        sql_expr = re.sub(r'USERATTRIBUTE\("([^"]+)"\)', attr_replacer, sql_expr, flags=re.IGNORECASE)
        sql_expr = re.sub(r"\[([^\]]+)\]", r'"\1"', sql_expr)

        return sql_expr

    def apply_rls_to_duckdb_query(self, base_sql: str, context: RLSUserContext) -> str:
        predicates = self.resolve_user_predicates(context)
        if not predicates:
            return base_sql

        cte_definitions = []
        for table_name, predicate in predicates.items():
            cte_definitions.append(
                f'"{table_name}_rls" AS (SELECT * FROM "{table_name}" WHERE {predicate})'
            )

        if not cte_definitions:
            return base_sql

        cte_prefix = "WITH " + ", ".join(cte_definitions) + "\n"

        modified_sql = base_sql
        for table_name in predicates.keys():
            modified_sql = re.sub(
                rf'\bFROM\s+"?{table_name}"?\b',
                f'FROM "{table_name}_rls"',
                modified_sql,
                flags=re.IGNORECASE,
            )
            modified_sql = re.sub(
                rf'\bJOIN\s+"?{table_name}"?\b',
                f'JOIN "{table_name}_rls"',
                modified_sql,
                flags=re.IGNORECASE,
            )

        return cte_prefix + modified_sql

    def build_where_clause(self, jwt_claims: Dict[str, Any], target_table: Optional[str] = None) -> str:
        """Construct a sanitized SQL WHERE clause from user claims."""
        dummy_query = f"SELECT * FROM {target_table or 'data'}"
        filtered = apply_rls_filters(dummy_query, jwt_claims, target_table=target_table)
        match = re.search(r"\bWHERE\b\s+(.*)", filtered, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""

    def sanitize_query(self, query: str, jwt_claims: Dict[str, Any], target_table: Optional[str] = None) -> str:
        """Inject RLS constraints directly into SQL query string."""
        return apply_rls_filters(query, jwt_claims, target_table=target_table)
