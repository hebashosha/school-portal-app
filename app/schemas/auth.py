# app/schemas/auth.py
import uuid
from typing import List, Optional
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    username_or_email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: uuid.UUID
    username: str
    display_name: str
    roles: List[str]
    permissions: List[str]


class UserProfileResponse(BaseModel):
    user_id: uuid.UUID
    username: str
    email: EmailStr
    display_name: str
    phone: Optional[str] = None
    is_active: bool
    roles: List[str]
    permissions: List[str]

    model_config = {"from_attributes": True}