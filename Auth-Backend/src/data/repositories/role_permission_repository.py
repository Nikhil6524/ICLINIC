from uuid import UUID

from sqlalchemy.orm import Session

from src.data.models.postgres.role_permission import RolePermission
from src.data.models.postgres.permission import Permission


class RolePermissionRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, role_permission: RolePermission) -> None:
        self.db.add(role_permission)

    def get_permissions_for_role(self, role_id: UUID) -> list[str]:
        """Get all permission names for a role."""
        results = (
            self.db.query(Permission.name)
            .join(
                RolePermission,
                RolePermission.permission_id == Permission.id
            )
            .filter(RolePermission.role_id == role_id)
            .all()
        )
        return [r[0] for r in results]

    def get_permissions_for_user_role(self, role_id: UUID) -> list[Permission]:
        """Get all Permission objects for a role."""
        return (
            self.db.query(Permission)
            .join(
                RolePermission,
                RolePermission.permission_id == Permission.id
            )
            .filter(RolePermission.role_id == role_id)
            .all()
        )

    def remove(self, role_id: UUID, permission_id: UUID) -> None:
        self.db.query(RolePermission).filter(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_id,
        ).delete()
