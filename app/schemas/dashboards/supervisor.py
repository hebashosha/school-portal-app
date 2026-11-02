import uuid
from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field


class SupervisorDashboardResponse(BaseModel):
    assigned_classes_count: int
    recorded_classes_today: int
    today_present_count: int
    today_absent_count: int
    today_late_count: int
    today_excused_count: int
    pending_manager_authorization_count: int


class StudentAttendanceEntry(BaseModel):
    student_id: uuid.UUID
    status: str = Field(..., pattern="^(PRESENT|ABSENT|LATE|EXCUSED)$")
    reason: Optional[str] = None


class SupervisorRecordAttendanceRequest(BaseModel):
    academic_year_id: uuid.UUID
    class_id: uuid.UUID
    occurrence_date: date
    period_number: Optional[int] = 1
    subject_id: Optional[uuid.UUID] = None
    records: List[StudentAttendanceEntry]


class SupervisorChangeRequestCreate(BaseModel):
    attendance_record_id: uuid.UUID
    new_status: str = Field(..., pattern="^(PRESENT|ABSENT|LATE|EXCUSED)$")
    reason: str = Field(..., min_length=5)