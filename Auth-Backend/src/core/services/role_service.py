from uuid import UUID

from sqlalchemy.orm import Session

from src.data.repositories.role_repository import RoleRepository
from src.data.repositories.role_permission_repository import RolePermissionRepository


class RoleService:
    def __init__(self, db: Session):
        self.db = db
        self.role_repo = RoleRepository(db)
        self.role_permission_repo = RolePermissionRepository(db)

    def get_role_permissions(self, role_name: str) -> list[str]:
        """Get all permission names for a role by role name."""
        role = self.role_repo.get_by_name(role_name)
        if not role:
            return []

        return self.role_permission_repo.get_permissions_for_role(role.id)

    def get_default_role_id(self) -> UUID | None:
        """Get the PATIENT role id (default for new users)."""
        role = self.role_repo.get_by_name("PATIENT")
        return role.id if role else None
