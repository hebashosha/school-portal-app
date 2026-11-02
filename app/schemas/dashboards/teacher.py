import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class HomeworkCard(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    assignment_id: uuid.UUID
    title: str
    class_id: uuid.UUID
    due_at: datetime
    submitted_count: int
    graded_count: int


class TeacherDashboardResponse(BaseModel):
    staff_code: str
    active_assignments_count: int
    pending_grading_count: int
    recent_assignments: List[HomeworkCard] = []


class TeacherCreateAssignmentRequest(BaseModel):
    class_id: uuid.UUID
    subject_id: uuid.UUID
    title: str = Field(..., min_length=3, max_length=255)
    instructions: Optional[str] = None
    assignment_type: str = Field(default="HYBRID", pattern="^(FILE_BASED|ONLINE_TEXT|HYBRID)$")
    max_score: Decimal = Field(default=Decimal("100.00"), gt=0)
    due_at: datetime
    allow_resubmission: bool = False
    max_attempts: int = Field(default=1, gt=0)


class TeacherGradeSubmissionRequest(BaseModel):
    awarded_score: Decimal = Field(..., ge=0, le=1000)
    teacher_feedback: Optional[str] = None