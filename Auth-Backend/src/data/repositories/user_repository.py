from uuid import UUID

from sqlalchemy.orm import Session

from src.data.models.postgres.user import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, user: User) -> None:
        self.db.add(user)

    def get_by_id(self, user_id: UUID) -> User | None:
        return (
            self.db.query(User)
            .filter(User.id == user_id)
            .first()
        )

    def get_by_email(self, email: str) -> User | None:
        return (
            self.db.query(User)
            .filter(User.email == email)
            .first()
        )

    def get_all(self) -> list[User]:
        return self.db.query(User).all()

    def delete(self, user: User) -> None:
        self.db.delete(user)
