# app/schemas/user.py
import uuid
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


class RoleResponse(BaseModel):
    role_id: uuid.UUID
    role_code: str
    role_name: str

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    display_name: str
    phone: Optional[str] = None
    # No default value -> Must be provided explicitly in every request
    # min_length=1 ensures at least one role is provided
    roles: List[str] = Field(
        ...,
        min_length=1,
        description="List of role codes to assign (e.g. ['TEACHER'], ['STUDENT'], ['FLOOR_SUPERVISOR'])",
        examples=[["TEACHER"]],
    )


class UserResponse(BaseModel):
    user_id: uuid.UUID
    username: str
    email: EmailStr
    display_name: str
    phone: Optional[str] = None
    is_active: bool
    roles: List[RoleResponse] = []

    model_config = {"from_attributes": True}