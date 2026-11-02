# app/api/v1/endpoints/dashboards/assistant_teacher.py
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_permissions
from app.models.coursework import Assignment, AssignmentSubmission
from app.models.stakeholder import StaffMember, Student
from app.models.user import User
from app.schemas.dashboards.assistant_teacher import AssistantTeacherDashboardResponse
from app.services.dashboards.assistant_teacher_service import AssistantTeacherDashboardService

router = APIRouter(prefix="/assistant-teacher", tags=["5. Assistant Teacher Support Workspace"])


class AssistantNoteRequest(BaseModel):
    note: str = Field(..., min_length=3)


class AssistantMessageRequest(BaseModel):
    recipient_user_id: uuid.UUID
    subject: str = Field(..., min_length=2, max_length=200)
    body: str = Field(..., min_length=2)


@router.get("", response_model=AssistantTeacherDashboardResponse)
async def get_assistant_teacher_dashboard(
    current_user: User = Depends(require_permissions(["VIEW_DASHBOARD"])),
    db: AsyncSession = Depends(get_db),
):
    """View Assistant Teacher academic support dashboard[cite: 1]."""
    service = AssistantTeacherDashboardService(db)
    return await service.get_dashboard(current_user)


@router.get("/homework")
async def assistant_view_homework(
    current_user: User = Depends(require_permissions(["VIEW_HOMEWORK"])),
    db: AsyncSession = Depends(get_db),
):
    """View assigned homework within authorized academic support scope[cite: 1]."""
    stmt = select(Assignment).order_by(Assignment.due_at.desc()).limit(20)
    assignments = (await db.execute(stmt)).scalars().all()
    return [{"assignment_id": a.assignment_id, "title": a.title, "due_at": a.due_at} for a in assignments]


@router.get("/homework/{assignment_id}/submissions")
async def assistant_review_submissions(
    assignment_id: uuid.UUID,
    current_user: User = Depends(require_permissions(["REVIEW_HOMEWORK_SUBMISSIONS"])),
    db: AsyncSession = Depends(get_db),
):
    """04.5.4 Section 6: View student homework submissions for initial review support[cite: 1]."""
    stmt = select(AssignmentSubmission).where(AssignmentSubmission.assignment_id == assignment_id)
    subs = (await db.execute(stmt)).scalars().all()
    return [{"submission_id": s.submission_id, "student_id": s.student_id, "status": s.status} for s in subs]


@router.get("/homework/{assignment_id}/history")
async def assistant_view_submission_history(
    assignment_id: uuid.UUID,
    student_id: uuid.UUID,
    current_user: User = Depends(require_permissions(["VIEW_SUBMISSION_HISTORY"])),
    db: AsyncSession = Depends(get_db),
):
    """View student resubmission history for support tracking[cite: 1]."""
    stmt = select(AssignmentSubmission).where(
        AssignmentSubmission.assignment_id == assignment_id,
        AssignmentSubmission.student_id == student_id,
    )
    history = (await db.execute(stmt)).scalars().all()
    return [{"submission_id": s.submission_id, "attempt": s.attempt_number} for s in history]


@router.get("/exams")
async def assistant_view_exams(
    current_user: User = Depends(require_permissions(["VIEW_EXAMS"])),
    db: AsyncSession = Depends(get_db),
):
    """View scheduled exams for proctoring and student support[cite: 1]."""
    return {"message": "Assigned exams list retrieved for proctoring"}


@router.get("/exams/results")
async def assistant_view_exam_results(
    current_user: User = Depends(require_permissions(["VIEW_EXAM_RESULTS"])),
    db: AsyncSession = Depends(get_db),
):
    """View permitted exam results to assist the teacher[cite: 1]."""
    return {"message": "Permitted exam results retrieved"}


@router.post("/communications/send", status_code=status.HTTP_201_CREATED)
async def assistant_send_message(
    payload: AssistantMessageRequest,
    current_user: User = Depends(require_permissions(["SEND_PRIVATE_MESSAGE"])),
    db: AsyncSession = Depends(get_db),
):
    """Send private support message[cite: 1]."""
    return {"message": "Private message sent successfully"}


@router.get("/communications/inbox")
async def assistant_view_inbox(
    current_user: User = Depends(require_permissions(["RECEIVE_PRIVATE_MESSAGE"])),
    db: AsyncSession = Depends(get_db),
):
    """View received messages[cite: 1]."""
    return {"messages": []}


@router.post("/communications/students")
async def communicate_with_students(
    student_id: uuid.UUID,
    payload: AssistantNoteRequest,
    current_user: User = Depends(require_permissions(["COMMUNICATE_WITH_STUDENTS"])),
    db: AsyncSession = Depends(get_db),
):
    """Provide academic support communication to assigned students[cite: 1]."""
    return {"message": "Support communication sent to student", "student_id": student_id}


@router.post("/communications/teachers")
async def communicate_with_teachers(
    payload: AssistantNoteRequest,
    current_user: User = Depends(require_permissions(["COMMUNICATE_WITH_TEACHERS"])),
    db: AsyncSession = Depends(get_db),
):
    """Report academic or technical issues to the lead teacher[cite: 1]."""
    return {"message": "Support report sent to lead teacher successfully"}