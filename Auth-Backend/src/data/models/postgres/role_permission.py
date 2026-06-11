import uuid
from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy import ForeignKey

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from src.data.models.postgres.base import Base


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("roles.id"),
        primary_key=True
    )

    permission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("permissions.id"),
        primary_key=True
    )

    assigned_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
