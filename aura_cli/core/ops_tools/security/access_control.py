"""Access-control system for Aura CLI.

Provides permission management, roles and granular access control.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)


class Permission(Enum):
    """Available permission definitions."""

    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    DELETE = "delete"
    ADMIN = "admin"


@dataclass
class Role:
    """User/agent role (id, name, permissions)."""

    id: str
    name: str
    permissions: Set[Permission]
    description: str = ""


class AccessControl:
    """Manages role-based access control."""

    def __init__(self):
        """Initialise the access-control system."""
        self.roles: Dict[str, Role] = {}
        self.user_roles: Dict[str, List[str]] = {}
        self.stats = get_stats()

        self._create_default_roles()

        logger.info("AccessControl initialized")

    def _create_default_roles(self) -> None:
        """Create the default roles."""
        import uuid

        admin_role = Role(
            id=str(uuid.uuid4())[:8],
            name="admin",
            permissions=set(Permission),
            description="Acesso completo",
        )
        self.roles[admin_role.id] = admin_role

        dev_role = Role(
            id=str(uuid.uuid4())[:8],
            name="developer",
            permissions={Permission.READ, Permission.WRITE, Permission.EXECUTE},
            description="Acesso de desenvolvedor",
        )
        self.roles[dev_role.id] = dev_role

        read_only_role = Role(
            id=str(uuid.uuid4())[:8],
            name="read_only",
            permissions={Permission.READ},
            description="Apenas leitura",
        )
        self.roles[read_only_role.id] = read_only_role

        logger.debug("Default roles created")

    def create_role(
        self, name: str, permissions: Set[Permission], description: str = ""
    ) -> Role:
        """Create a new role with given permissions."""
        import uuid

        role = Role(
            id=str(uuid.uuid4())[:8],
            name=name,
            permissions=permissions,
            description=description,
        )

        self.roles[role.id] = role

        logger.info(f"Role '{name}' created")

        return role

    def assign_role(self, user_id: str, role_id: str) -> None:
        """Assign a role to a user."""
        if role_id not in self.roles:
            raise ValueError(f"Role {role_id} not found")

        if user_id not in self.user_roles:
            self.user_roles[user_id] = []

        if role_id not in self.user_roles[user_id]:
            self.user_roles[user_id].append(role_id)
            logger.info(f"Role {role_id} atribuído ao usuário {user_id}")

    def check_permission(self, user_id: str, permission: Permission) -> bool:
        """Check if a role has a specific permission."""
        role_ids = self.user_roles.get(user_id, [])

        for role_id in role_ids:
            role = self.roles.get(role_id)
            if role and permission in role.permissions:
                return True

        return False

    def get_user_permissions(self, user_id: str) -> Set[Permission]:
        """Return all permissions for a user role."""
        permissions = set()
        role_ids = self.user_roles.get(user_id, [])

        for role_id in role_ids:
            role = self.roles.get(role_id)
            if role:
                permissions.update(role.permissions)

        return permissions

    def list_roles(self) -> List[Dict[str, Any]]:
        """Return a list of all roles."""
        return [
            {
                "id": r.id,
                "name": r.name,
                "permissions": [p.value for p in r.permissions],
                "description": r.description,
            }
            for r in self.roles.values()
        ]


# Factory function for singleton pattern
_access_control_instance: Optional[AccessControl] = None


def get_access_control() -> AccessControl:
    """
    Get or create AccessControl instance (singleton).

    Returns:
        AccessControl instance
    """
    global _access_control_instance
    if _access_control_instance is None:
        _access_control_instance = AccessControl()
    return _access_control_instance
