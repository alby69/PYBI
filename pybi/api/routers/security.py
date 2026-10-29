from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException

from pybi.models.security import RLSUserContext, SecurityRole, UserRoleMapping
from pybi.core.rls_engine import RLSEngine

router = APIRouter(prefix="/api/v1/security", tags=["Security RLS"])

roles_db: Dict[str, SecurityRole] = {}
mappings_db: Dict[str, UserRoleMapping] = {}


@router.get("/roles", response_model=List[SecurityRole])
async def list_security_roles():
    return list(roles_db.values())


@router.post("/roles", response_model=SecurityRole)
async def create_or_update_role(role: SecurityRole):
    roles_db[role.role_id] = role
    return role


@router.delete("/roles/{role_id}")
async def delete_role(role_id: str):
    if role_id in roles_db:
        del roles_db[role_id]
        return {"status": "success", "message": f"Ruolo {role_id} eliminato"}
    raise HTTPException(status_code=404, detail="Ruolo non trovato")


@router.post("/test-context")
async def evaluate_rls_predicates(context: RLSUserContext):
    engine = RLSEngine(semantic_model=None, roles=list(roles_db.values()))
    predicates = engine.resolve_user_predicates(context)
    return {
        "user_id": context.user_id,
        "effective_roles": context.effective_roles,
        "generated_predicates": predicates,
    }
