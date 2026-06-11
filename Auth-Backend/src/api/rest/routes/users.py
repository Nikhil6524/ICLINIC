from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends

from src.api.rest.dependencies import DBSession
from src.api.rest.dependencies import CurrentUser
from src.api.rest.dependencies import require_role
from src.api.rest.dependencies import require_permission
from src.core.services.user_service import UserService
from src.schemas.auth.user_response import UserResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(
    current_user: CurrentUser,
    db: DBSession,
):
    user_service = UserService(db)
    return user_service.get_user_with_role(current_user["sub"])


@router.patch("/me/profile-complete")
def mark_profile_completed(
    current_user: CurrentUser,
    db: DBSession,
):
    user_service = UserService(db)
    user_service.mark_profile_completed(current_user["sub"])
    return {"message": "Profile marked as completed"}


@router.get(
    "/all",
    response_model=list[UserResponse],
    dependencies=[Depends(require_permission("user.manage"))],
)
def get_all_users(
    db: DBSession,
):
    """Admin-only endpoint to list all users."""
    user_service = UserService(db)
    return user_service.get_all_users()


@router.patch(
    "/{user_id}/deactivate",
    dependencies=[Depends(require_permission("user.manage"))],
)
def deactivate_user(
    user_id: UUID,
    db: DBSession,
):
    user_service = UserService(db)
    user_service.deactivate_user(user_id)
    return {"message": "User deactivated"}


@router.patch(
    "/{user_id}/activate",
    dependencies=[Depends(require_permission("user.manage"))],
)
def activate_user(
    user_id: UUID,
    db: DBSession,
):
    user_service = UserService(db)
    user_service.activate_user(user_id)
    return {"message": "User activated"}
