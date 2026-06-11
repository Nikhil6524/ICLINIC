from uuid import UUID

from sqlalchemy.orm import Session

from src.data.models.postgres.role import Role


class RoleRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, role: Role) -> None:
        self.db.add(role)

    def get_by_id(self, role_id: UUID) -> Role | None:
        return (
            self.db.query(Role)
            .filter(Role.id == role_id)
            .first()
        )

    def get_by_name(self, name: str) -> Role | None:
        return (
            self.db.query(Role)
            .filter(Role.name == name)
            .first()
        )

    def get_all(self) -> list[Role]:
        return self.db.query(Role).all()
