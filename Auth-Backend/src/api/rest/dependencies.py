from typing import Annotated

from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request
from fastapi import status
from sqlalchemy.orm import Session

from src.core.services.jwt_service import JWTService
from src.core.services.authorization_service import AuthorizationService
from src.data.clients.postgres_client import get_db


DBSession = Annotated[
    Session,
    Depends(get_db)
]


def get_current_user(request: Request) -> dict:
    """Extract and validate the current user from the access token cookie."""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    payload = JWTService.decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    return payload


CurrentUser = Annotated[
    dict,
    Depends(get_current_user)
]


def require_role(*allowed_roles: str):
    """Dependency factory to enforce role-based access."""
    def role_checker(current_user: CurrentUser) -> dict:
        user_role = current_user.get("role")
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    return role_checker


def require_permission(permission: str):
    """Dependency factory to enforce permission-based access."""
    def permission_checker(
        current_user: CurrentUser,
        db: DBSession,
    ) -> dict:
        auth_service = AuthorizationService(db)
        user_id = current_user.get("sub")

        if not auth_service.has_permission(user_id, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission}"
            )
        return current_user
    return permission_checker
