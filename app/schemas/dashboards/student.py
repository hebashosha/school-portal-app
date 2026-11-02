import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class StudentTaskItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    item_type: str
    due_at: datetime
    status: str
    awarded_score: Optional[Decimal] = None


class StudentDashboardResponse(BaseModel):
    student_code: str
    student_name: str
    today_attendance_status: str
    upcoming_tasks: List[StudentTaskItem] = []


class StudentSubmitAssignmentRequest(BaseModel):
    text_solution: Optional[str] = None
    attachment_storage_keys: List[str] = []