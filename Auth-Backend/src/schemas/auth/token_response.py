from pydantic import BaseModel


class TokenResponse(BaseModel):
    access_token: str
    profile_completed: bool
