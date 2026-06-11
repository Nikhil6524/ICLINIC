from src.core.services.password_service import PasswordService


def hash_password(password: str) -> str:
    """Hash a plain text password."""
    return PasswordService.hash_password(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain text password against a hash."""
    return PasswordService.verify_password(plain_password, hashed_password)
