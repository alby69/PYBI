"""Casbin-backed Role-Based Access Control (RBAC) manager for PyBI."""

from typing import List, Optional
import casbin
from casbin.model import Model

MODEL_CONF = """
[request_definition]
r = sub, obj, act

[policy_definition]
p = sub, obj, act

[role_definition]
g = _, _

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = g(r.sub, p.sub) && keyMatch(r.obj, p.obj) && regexMatch(r.act, p.act)
"""

DEFAULT_POLICIES = [
    # Admin role can do everything on all resources
    ("admin", "*", ".*"),
    # Editor role can read/write projects, ETL pipelines, and dashboards
    ("editor", "project", "read|write"),
    ("editor", "etl", "read|execute|write"),
    ("editor", "dashboard", "read|write"),
    # Viewer role can read projects, executed ETL, and view dashboards
    ("viewer", "project", "read"),
    ("viewer", "etl", "read|execute"),
    ("viewer", "dashboard", "read"),
]


class RBACManager:
    """RBACManager handles Casbin permission checking and role assignments."""

    def __init__(self, model_path: Optional[str] = None, policy_path: Optional[str] = None) -> None:
        """Initialize Casbin Enforcer with inline default model or config file.

        Args:
            model_path: Optional path to custom model.conf file.
            policy_path: Optional path to custom policy.csv file.
        """
        if model_path and policy_path:
            self.enforcer = casbin.Enforcer(model_path, policy_path)
        else:
            model = Model()
            model.load_model_from_text(MODEL_CONF)
            self.enforcer = casbin.Enforcer(model)
            self._load_default_policies()

    def _load_default_policies(self) -> None:
        """Load default role-permission mappings."""
        for role, obj, act in DEFAULT_POLICIES:
            self.enforcer.add_policy(role, obj, act)

    def enforce(self, sub: str, obj: str, act: str) -> bool:
        """Check whether subject `sub` has permission to perform `act` on `obj`.

        Args:
            sub: Subject (user identifier or role).
            obj: Object / resource (e.g. 'project', 'dashboard', 'etl').
            act: Action (e.g. 'read', 'write', 'execute').

        Returns:
            bool: True if access is granted.
        """
        return self.enforcer.enforce(sub, obj, act)

    def add_user_role(self, username: str, role: str) -> bool:
        """Assign a role to a user.

        Args:
            username: User identifier.
            role: Role name (e.g. 'admin', 'editor', 'viewer').

        Returns:
            bool: True if role added.
        """
        return self.enforcer.add_grouping_policy(username, role)

    def remove_user_role(self, username: str, role: str) -> bool:
        """Remove a role assignment from a user.

        Args:
            username: User identifier.
            role: Role name.

        Returns:
            bool: True if role removed.
        """
        return self.enforcer.remove_grouping_policy(username, role)

    def get_roles_for_user(self, username: str) -> List[str]:
        """Get list of assigned roles for a user.

        Args:
            username: User identifier.

        Returns:
            List[str]: Role names assigned to user.
        """
        return self.enforcer.get_roles_for_user(username)


# Global singleton instance with default RBAC setup
default_rbac = RBACManager()
