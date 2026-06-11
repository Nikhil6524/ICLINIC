from uuid import UUID

from pydantic import BaseModel
from pydantic import EmailStr


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    role: str
    profile_completed: bool
    is_active: bool
