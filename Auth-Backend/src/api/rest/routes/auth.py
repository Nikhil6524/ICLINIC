from fastapi import APIRouter
from fastapi import Request
from fastapi import Response
from fastapi import HTTPException
from fastapi import status

from src.api.rest.dependencies import DBSession
from src.core.services.auth_service import AuthService
from src.schemas.auth.register_request import RegisterRequest
from src.schemas.auth.login_request import LoginRequest
from src.schemas.auth.token_response import TokenResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=TokenResponse)
def register(
    request: RegisterRequest,
    response: Response,
    db: DBSession,
):
    auth_service = AuthService(db)
    result = auth_service.register(request)

    # Set HTTP-only cookies
    response.set_cookie(
        key="access_token",
        value=result["access_token"],
        httponly=True,
        secure=True,
        samesite="lax",
    )
    response.set_cookie(
        key="refresh_token",
        value=result["refresh_token"],
        httponly=True,
        secure=True,
        samesite="lax",
    )

    return TokenResponse(
        access_token=result["access_token"],
        profile_completed=result["profile_completed"],
    )


@router.post("/login", response_model=TokenResponse)
def login(
    request: LoginRequest,
    response: Response,
    db: DBSession,
):
    auth_service = AuthService(db)
    result = auth_service.login(request)

    # Set HTTP-only cookies
    response.set_cookie(
        key="access_token",
        value=result["access_token"],
        httponly=True,
        secure=True,
        samesite="lax",
    )
    response.set_cookie(
        key="refresh_token",
        value=result["refresh_token"],
        httponly=True,
        secure=True,
        samesite="lax",
    )

    return TokenResponse(
        access_token=result["access_token"],
        profile_completed=result["profile_completed"],
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    raw_request: Request,
    response: Response,
    db: DBSession,
):
    refresh_token = raw_request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found"
        )

    auth_service = AuthService(db)
    result = auth_service.refresh(refresh_token)

    # Set new HTTP-only cookies
    response.set_cookie(
        key="access_token",
        value=result["access_token"],
        httponly=True,
        secure=True,
        samesite="lax",
    )
    response.set_cookie(
        key="refresh_token",
        value=result["refresh_token"],
        httponly=True,
        secure=True,
        samesite="lax",
    )

    return TokenResponse(
        access_token=result["access_token"],
        profile_completed=result["profile_completed"],
    )


@router.post("/logout")
def logout(
    raw_request: Request,
    response: Response,
    db: DBSession,
):
    refresh_token = raw_request.cookies.get("refresh_token")
    if refresh_token:
        auth_service = AuthService(db)
        auth_service.logout(refresh_token)

    # Clear cookies
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")

    return {"message": "Logged out successfully"}
