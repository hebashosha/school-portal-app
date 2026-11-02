import uuid
from datetime import date
from typing import Dict, List, Optional
from pydantic import BaseModel, EmailStr, Field


class AdminDashboardResponse(BaseModel):
    user_counts_by_role: Dict[str, int]
    total_users: int
    active_users: int
    inactive_users: int
    active_academic_year: Optional[str] = None
    total_grades: int
    total_classes: int
    total_subjects: int
    today_attendance_summary: Dict[str, int]
    recent_audit_count: int


class AdminCreateUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    display_name: str
    role_code: str = Field(
        ...,
        pattern="^(SCHOOL_ADMIN|DIRECTOR|FLOOR_SUPERVISOR|TEACHER|ASSISTANT_TEACHER|STUDENT|PARENT)$",
    )
    employee_code: Optional[str] = None
    student_code: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None


class AdminToggleUserStatusRequest(BaseModel):
    is_active: bool


class AdminLinkParentStudentRequest(BaseModel):
    parent_user_id: uuid.UUID
    student_id: uuid.UUID
    relationship_type: str = Field(default="FATHER", example="FATHER")
    is_primary: bool = True