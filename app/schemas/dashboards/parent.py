import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class LinkedStudentCard(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    student_id: uuid.UUID
    student_code: str
    full_name: str
    today_attendance: str
    pending_homework_count: int


class ParentDashboardResponse(BaseModel):
    parent_name: str
    total_linked_children: int
    children: List[LinkedStudentCard] = []


class ChildSubmissionReportItem(BaseModel):
    submission_id: uuid.UUID
    assignment_id: uuid.UUID
    status: str
    submitted_at: datetime
    awarded_score: Optional[Decimal] = None
    teacher_feedback: Optional[str] = None


class ChildDetailedReportResponse(BaseModel):
    student_id: uuid.UUID
    full_name: str
    student_code: str
    recent_attendance: List[str] = []
    recent_submissions: List[ChildSubmissionReportItem] = []


class ParentAbsenceExcuseRequest(BaseModel):
    occurrence_date: date
    excuse_type: str = Field(..., pattern="^(EXCUSED|LATE)$")
    reason: str = Field(..., min_length=5)