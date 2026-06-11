from datetime import datetime
from datetime import timedelta

from jose import jwt
from jose import JWTError

from src.config.security import (
    JWT_SECRET_KEY,
    JWT_ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS
)


class JWTService:

    @staticmethod
    def create_access_token(
        user_id: str,
        email: str,
        role: str,
        profile_completed: bool
    ) -> str:
        expire = (
            datetime.utcnow()
            + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        payload = {
            "sub": user_id,
            "email": email,
            "role": role,
            "profile_completed": profile_completed,
            "exp": expire,
        }

        return jwt.encode(
            payload,
            JWT_SECRET_KEY,
            algorithm=JWT_ALGORITHM
        )

    @staticmethod
    def create_refresh_token(
        user_id: str
    ) -> str:
        expire = (
            datetime.utcnow()
            + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        )

        payload = {
            "sub": user_id,
            "exp": expire,
        }

        return jwt.encode(
            payload,
            JWT_SECRET_KEY,
            algorithm=JWT_ALGORITHM
        )

    @staticmethod
    def decode_token(token: str) -> dict | None:
        try:
            return jwt.decode(
                token,
                JWT_SECRET_KEY,
                algorithms=[JWT_ALGORITHM]
            )
        except JWTError:
            return None
