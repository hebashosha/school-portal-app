import uuid
from typing import List
from pydantic import BaseModel, Field


class AssistantTeacherDashboardResponse(BaseModel):
    staff_code: str
    active_assignments_to_follow: int
    unsubmitted_students_count: int


class UnsubmittedStudentItem(BaseModel):
    student_id: uuid.UUID
    student_code: str
    full_name: str


class AssistantFollowUpNoteRequest(BaseModel):
    note: str = Field(..., min_length=3)