from uuid import UUID

from sqlalchemy.orm import Session

from src.data.repositories.user_repository import UserRepository
from src.data.repositories.role_permission_repository import RolePermissionRepository


class AuthorizationService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.role_permission_repo = RolePermissionRepository(db)

    def has_permission(self, user_id: UUID, permission: str) -> bool:
        """Check if a user has a specific permission via their role."""
        user = self.user_repo.get_by_id(user_id)
        if not user:
            return False

        permissions = self.role_permission_repo.get_permissions_for_role(
            user.role_id
        )
        return permission in permissions

    def get_user_permissions(self, user_id: UUID) -> list[str]:
        """Get all permissions for a user via their role."""
        user = self.user_repo.get_by_id(user_id)
        if not user:
            return []

        return self.role_permission_repo.get_permissions_for_role(
            user.role_id
        )
