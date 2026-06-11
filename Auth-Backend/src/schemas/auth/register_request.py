from pydantic import BaseModel
from pydantic import EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    role: str = "PATIENT"
