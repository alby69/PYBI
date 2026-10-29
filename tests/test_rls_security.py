import pytest
from fastapi.testclient import TestClient

from pybi.api.main import app
from pybi.core.rls_engine import RLSEngine
from pybi.models.security import RLSUserContext, SecurityRole, TableFilterRule


def test_rls_predicate_translation():
    role = SecurityRole(
        role_id="manager_italy",
        role_name="Manager Italia",
        table_filters=[
            TableFilterRule(table_name="Sales", filter_expression="[Country] = 'Italy'"),
            TableFilterRule(table_name="Users", filter_expression="[Username] = USERNAME()"),
        ],
    )

    engine = RLSEngine(semantic_model=None, roles=[role])
    context = RLSUserContext(
        user_id="u123",
        username="mario.rossi@pybi.org",
        effective_roles=["manager_italy"],
    )

    predicates = engine.resolve_user_predicates(context)

    assert predicates["Sales"] == '"Country" = \'Italy\''
    assert predicates["Users"] == '"Username" = \'mario.rossi@pybi.org\''


def test_rls_query_injection():
    role = SecurityRole(
        role_id="r1",
        role_name="Filter Sales",
        table_filters=[TableFilterRule(table_name="Sales", filter_expression="[Amount] > 1000")],
    )
    engine = RLSEngine(semantic_model=None, roles=[role])
    context = RLSUserContext(user_id="u1", username="test", effective_roles=["r1"])

    base_sql = 'SELECT * FROM "Sales" JOIN "Customers" ON Sales.customer_id = Customers.id'
    modified_sql = engine.apply_rls_to_duckdb_query(base_sql, context)

    assert 'WITH "Sales_rls" AS (SELECT * FROM "Sales" WHERE "Amount" > 1000)' in modified_sql
    assert 'FROM "Sales_rls"' in modified_sql


def test_rls_user_attribute_replacement():
    role = SecurityRole(
        role_id="r_attr",
        role_name="Region Filter",
        table_filters=[TableFilterRule(table_name="Sales", filter_expression='[Region] = USERATTRIBUTE("Region")')],
    )
    engine = RLSEngine(semantic_model=None, roles=[role])
    context = RLSUserContext(
        user_id="u2",
        username="user2",
        effective_roles=["r_attr"],
        custom_attributes={"Region": "EMEA"},
    )

    predicates = engine.resolve_user_predicates(context)
    assert predicates["Sales"] == '"Region" = \'EMEA\''


def test_rls_security_api_endpoints():
    client = TestClient(app)

    # 1. Create Role
    role_payload = {
        "role_id": "test_role_1",
        "role_name": "Test Role 1",
        "description": "Role for testing",
        "table_filters": [
            {"table_name": "Sales", "filter_expression": "[Amount] > 500", "is_active": True}
        ],
    }
    res = client.post("/api/v1/security/roles", json=role_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["role_id"] == "test_role_1"

    # 2. List Roles
    res_list = client.get("/api/v1/security/roles")
    assert res_list.status_code == 200
    roles = res_list.json()
    assert any(r["role_id"] == "test_role_1" for r in roles)

    # 3. Test Context Evaluation
    eval_payload = {
        "user_id": "user_api",
        "username": "api.user@pybi.org",
        "effective_roles": ["test_role_1"],
        "custom_attributes": {},
        "is_simulated": False,
    }
    res_eval = client.post("/api/v1/security/test-context", json=eval_payload)
    assert res_eval.status_code == 200
    eval_data = res_eval.json()
    assert eval_data["generated_predicates"]["Sales"] == '"Amount" > 500'

    # 4. Delete Role
    res_del = client.delete("/api/v1/security/roles/test_role_1")
    assert res_del.status_code == 200
