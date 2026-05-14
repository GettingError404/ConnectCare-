from pydantic import BaseModel, EmailStr, Field
from uuid import UUID
from datetime import datetime

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str = Field(min_length=1, max_length=150)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPair(TokenResponse):
    refresh_token: str

class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    name: str
    created_at: datetime
    model_config = {"from_attributes": True}


class RefreshRequest(BaseModel):
    refresh_token: str
