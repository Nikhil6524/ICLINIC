from fastapi import Response


def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
) -> None:
    """Set HTTP-only auth cookies on the response."""
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="lax",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
    )


def clear_auth_cookies(response: Response) -> None:
    """Remove auth cookies from the response."""
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")
