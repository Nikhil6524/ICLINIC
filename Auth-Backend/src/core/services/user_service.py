from uuid import UUID

from fastapi import HTTPException
from fastapi import status
from sqlalchemy.orm import Session

from src.data.repositories.user_repository import UserRepository
from src.data.repositories.role_repository import RoleRepository


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.role_repo = RoleRepository(db)

    def get_user_with_role(self, user_id: UUID) -> dict:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        role = self.role_repo.get_by_id(user.role_id)
        role_name = role.name if role else "PATIENT"

        return {
            "id": user.id,
            "email": user.email,
            "role": role_name,
            "profile_completed": user.profile_completed,
            "is_active": user.is_active,
        }

    def mark_profile_completed(self, user_id: UUID) -> None:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        user.profile_completed = True

    def get_all_users(self) -> list[dict]:
        users = self.user_repo.get_all()
        result = []
        for u in users:
            role = self.role_repo.get_by_id(u.role_id)
            role_name = role.name if role else "PATIENT"
            result.append({
                "id": u.id,
                "email": u.email,
                "role": role_name,
                "profile_completed": u.profile_completed,
                "is_active": u.is_active,
            })
        return result

    def deactivate_user(self, user_id: UUID) -> None:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        user.is_active = False

    def activate_user(self, user_id: UUID) -> None:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        user.is_active = True
