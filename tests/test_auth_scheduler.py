"""Unit tests for Auth (JWT & Casbin RBAC) and ETLScheduler modules."""

import asyncio
import pytest

from pybi.auth import (
    AuthUser,
    RBACManager,
    create_access_token,
    decode_access_token,
    default_rbac,
    hash_password,
    verify_password,
)
from pybi.etl.scheduler import ETLScheduler


def test_password_hashing():
    pwd = "my_secure_password"
    hashed = hash_password(pwd)
    assert "$" in hashed
    assert verify_password(pwd, hashed) is True
    assert verify_password("wrong_password", hashed) is False


def test_jwt_token_generation_and_decoding():
    payload = {"sub": "alice", "role": "editor"}
    token = create_access_token(payload)
    assert isinstance(token, str)

    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "alice"
    assert decoded["role"] == "editor"


def test_jwt_invalid_token():
    assert decode_access_token("invalid.jwt.token") is None


def test_rbac_manager_permissions():
    rbac = RBACManager()

    # Admin role permissions
    assert rbac.enforce("admin", "project", "read") is True
    assert rbac.enforce("admin", "etl", "write") is True

    # Editor role permissions
    assert rbac.enforce("editor", "project", "write") is True
    assert rbac.enforce("editor", "dashboard", "read") is True

    # Viewer role permissions
    assert rbac.enforce("viewer", "project", "read") is True
    assert rbac.enforce("viewer", "project", "write") is False


def test_rbac_user_role_assignment():
    rbac = RBACManager()
    rbac.add_user_role("bob", "editor")

    assert "editor" in rbac.get_roles_for_user("bob")
    assert rbac.enforce("bob", "project", "write") is True

    rbac.remove_user_role("bob", "editor")
    assert "editor" not in rbac.get_roles_for_user("bob")
    assert rbac.enforce("bob", "project", "write") is False


@pytest.mark.asyncio
async def test_etl_scheduler():
    scheduler = ETLScheduler()
    executed_tasks = []

    def on_complete(task_id, result):
        executed_tasks.append((task_id, result.status))

    dag = {"nodes": [], "edges": []}
    scheduler.schedule_pipeline("test_task", dag, interval_seconds=1, on_complete=on_complete)

    await asyncio.sleep(0.2)

    status = scheduler.get_task_status("test_task")
    assert status is not None
    assert status["is_running"] is True
    assert status["run_count"] >= 1
    assert len(executed_tasks) >= 1
    assert executed_tasks[0][0] == "test_task"

    assert scheduler.cancel_pipeline("test_task") is True
    assert scheduler.get_task_status("test_task") is None
