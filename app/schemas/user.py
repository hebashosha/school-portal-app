# app/schemas/user.py
import uuid
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field

# Request DTO: Create
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    display_name: str = Field(..., min_length=1, max_length=200)
    phone: Optional[str] = None

# Request DTO: Update
class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None

# Response DTO
class UserResponse(BaseModel):
    user_id: uuid.UUID
    username: str
    email: EmailStr
    display_name: str
    phone: Optional[str]
    is_active: bool

    # Spring Equivalent: maps JPA Entity attributes into DTO fields
    model_config = ConfigDict(from_attributes=True)