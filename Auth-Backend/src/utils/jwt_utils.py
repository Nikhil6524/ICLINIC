from src.core.services.jwt_service import JWTService


def decode_access_token(token: str) -> dict | None:
    """Decode and validate an access token. Returns payload or None."""
    return JWTService.decode_token(token)
