from uuid import UUID

from sqlalchemy.orm import Session

from src.data.models.postgres.permission import Permission


class PermissionRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, permission: Permission) -> None:
        self.db.add(permission)

    def get_by_id(self, permission_id: UUID) -> Permission | None:
        return (
            self.db.query(Permission)
            .filter(Permission.id == permission_id)
            .first()
        )

    def get_by_name(self, name: str) -> Permission | None:
        return (
            self.db.query(Permission)
            .filter(Permission.name == name)
            .first()
        )

    def get_all(self) -> list[Permission]:
        return self.db.query(Permission).all()
