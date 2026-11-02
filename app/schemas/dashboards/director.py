import uuid
from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ApprovalQueueItem(BaseModel):
    request_id: uuid.UUID
    request_type: str
    details: str
    requested_at: datetime


class DirectorDashboardResponse(BaseModel):
    pending_approvals_count: int
    pending_late_approvals: int
    pending_excused_approvals: int
    pending_attendance_changes: int
    today_attendance_summary: Dict[str, int]
    recent_approvals_queue: List[ApprovalQueueItem] = []


class DirectorReviewChangeRequest(BaseModel):
    decision: str = Field(..., pattern="^(APPROVED|REJECTED)$")
    reason_notes: Optional[str] = None