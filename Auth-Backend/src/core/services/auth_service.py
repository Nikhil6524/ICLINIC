import hashlib
from datetime import datetime
from datetime import timedelta

from fastapi import HTTPException
from fastapi import status
from sqlalchemy.orm import Session

from src.config.security import REFRESH_TOKEN_EXPIRE_DAYS
from src.core.services.jwt_service import JWTService
from src.core.services.password_service import PasswordService
from src.data.models.postgres.user import User
from src.data.models.postgres.refresh_token import RefreshToken
from src.data.repositories.user_repository import UserRepository
from src.data.repositories.role_repository import RoleRepository
from src.data.repositories.refresh_token_repository import RefreshTokenRepository
from src.schemas.auth.register_request import RegisterRequest
from src.schemas.auth.login_request import LoginRequest

VALID_ROLES = {"ADMIN", "DOCTOR", "FRONT_DESK", "PATIENT"}


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.role_repo = RoleRepository(db)
        self.refresh_token_repo = RefreshTokenRepository(db)

    def register(self, request: RegisterRequest) -> dict:
        # Validate role
        role_name = request.role.upper()
        if role_name not in VALID_ROLES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}"
            )

        # Check if user already exists
        existing_user = self.user_repo.get_by_email(request.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists"
            )

        # Lookup role
        role = self.role_repo.get_by_name(role_name)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role '{role_name}' not found in database"
            )

        # Create user with role_id
        password_hash = PasswordService.hash_password(request.password)
        user = User(
            email=request.email,
            password_hash=password_hash,
            role_id=role.id,
        )
        self.user_repo.add(user)
        self.db.flush()

        # Generate tokens
        access_token = JWTService.create_access_token(
            user_id=str(user.id),
            email=user.email,
            role=role_name,
            profile_completed=user.profile_completed,
        )
        refresh_token = JWTService.create_refresh_token(
            user_id=str(user.id)
        )
        self._store_refresh_token(user.id, refresh_token)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "profile_completed": user.profile_completed,
        }

    def login(self, request: LoginRequest) -> dict:
        # Find user
        user = self.user_repo.get_by_email(request.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        # Verify password
        if not PasswordService.verify_password(
            request.password, user.password_hash
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated"
            )

        # Get role name
        role = self.role_repo.get_by_id(user.role_id)
        role_name = role.name if role else "PATIENT"

        # Generate tokens
        access_token = JWTService.create_access_token(
            user_id=str(user.id),
            email=user.email,
            role=role_name,
            profile_completed=user.profile_completed,
        )
        refresh_token = JWTService.create_refresh_token(
            user_id=str(user.id)
        )
        self._store_refresh_token(user.id, refresh_token)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "profile_completed": user.profile_completed,
        }

    def refresh(self, refresh_token: str) -> dict:
        # Decode refresh token
        payload = JWTService.decode_token(refresh_token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )

        # Verify the token hash exists and is not revoked
        token_hash = self._hash_token(refresh_token)
        stored_token = self.refresh_token_repo.get_by_token_hash(token_hash)

        if not stored_token or stored_token.is_revoked:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or revoked refresh token"
            )

        # Check expiry
        if stored_token.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired"
            )

        # Revoke old token
        self.refresh_token_repo.revoke(stored_token)

        # Get user
        user_id = payload.get("sub")
        user = self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )

        # Get role name
        role = self.role_repo.get_by_id(user.role_id)
        role_name = role.name if role else "PATIENT"

        # Generate new tokens
        access_token = JWTService.create_access_token(
            user_id=str(user.id),
            email=user.email,
            role=role_name,
            profile_completed=user.profile_completed,
        )
        new_refresh_token = JWTService.create_refresh_token(
            user_id=str(user.id)
        )
        self._store_refresh_token(user.id, new_refresh_token)

        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "profile_completed": user.profile_completed,
        }

    def logout(self, refresh_token: str) -> None:
        token_hash = self._hash_token(refresh_token)
        stored_token = self.refresh_token_repo.get_by_token_hash(token_hash)

        if stored_token and not stored_token.is_revoked:
            self.refresh_token_repo.revoke(stored_token)

    def _store_refresh_token(self, user_id, raw_token: str) -> None:
        token_hash = self._hash_token(raw_token)
        expires_at = (
            datetime.utcnow()
            + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        )

        refresh_token_record = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.refresh_token_repo.add(refresh_token_record)

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()
