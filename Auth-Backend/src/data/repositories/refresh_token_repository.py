from uuid import UUID

from sqlalchemy.orm import Session

from src.data.models.postgres.refresh_token import RefreshToken


class RefreshTokenRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, refresh_token: RefreshToken) -> None:
        self.db.add(refresh_token)

    def get_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        return (
            self.db.query(RefreshToken)
            .filter(RefreshToken.token_hash == token_hash)
            .first()
        )

    def revoke(self, refresh_token: RefreshToken) -> None:
        refresh_token.is_revoked = True

    def revoke_all_for_user(self, user_id: UUID) -> None:
        self.db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked == False  # noqa: E712
        ).update({"is_revoked": True})
