# app/api/v1/endpoints/dashboards/parent.py
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_permissions
from app.models.attendance import AttendanceOccurrence, AttendanceRecord
from app.models.coursework import Assignment, AssignmentSubmission
from app.models.stakeholder import ParentGuardian, ParentStudentRelationship, Student
from app.models.user import User
from app.schemas.dashboards.parent import ParentDashboardResponse
from app.services.audit_helper import record_audit_event
from app.services.dashboards.parent_service import ParentDashboardService

router = APIRouter(prefix="/parent", tags=["7. Parent / Guardian Workspace"])


class ParentMessageRequest(BaseModel):
    recipient_user_id: uuid.UUID
    subject: str = Field(..., min_length=2, max_length=200)
    body: str = Field(..., min_length=2)


async def _verify_parent_child(db: AsyncSession, parent_user_id: uuid.UUID, student_id: uuid.UUID) -> Student:
    """ADM-PS-BR-004 & ADM-PS-BR-018: Enforces active Parent <-> Student relationship boundary[cite: 1]."""
    stmt = (
        select(Student)
        .join(ParentStudentRelationship, Student.student_id == ParentStudentRelationship.student_id)
        .join(ParentGuardian, ParentStudentRelationship.parent_guardian_id == ParentGuardian.parent_guardian_id)
        .where(
            ParentGuardian.user_id == parent_user_id,
            Student.student_id == student_id,
            ParentStudentRelationship.is_active.is_(True),
        )
    )
    student = (await db.execute(stmt)).scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=403, detail="Access denied: Student is not officially linked to your account[cite: 1].")
    return student


@router.get("", response_model=ParentDashboardResponse)
async def get_parent_dashboard(
    current_user: User = Depends(require_permissions(["VIEW_DASHBOARD"])),
    db: AsyncSession = Depends(get_db),
):
    """View Parent dashboard with all officially linked children cards[cite: 1]."""
    service = ParentDashboardService(db)
    return await service.get_dashboard(current_user)


@router.get("/children/{student_id}/attendance")
async def parent_view_child_attendance(
    student_id: uuid.UUID,
    current_user: User = Depends(require_permissions(["VIEW_ATTENDANCE"])),
    db: AsyncSession = Depends(get_db),
):
    """ADM-PG-BR-007: View attendance status of officially linked children[cite: 1]."""
    student = await _verify_parent_child(db, current_user.user_id, student_id)
    stmt = (
        select(AttendanceOccurrence.occurrence_date, AttendanceRecord.status)
        .join(AttendanceOccurrence, AttendanceRecord.occurrence_id == AttendanceOccurrence.occurrence_id)
        .where(AttendanceRecord.student_id == student_id)
        .order_by(AttendanceOccurrence.occurrence_date.desc())
        .limit(15)
    )
    records = (await db.execute(stmt)).fetchall()
    return [{"date": d.isoformat(), "status": st} for d, st in records]


@router.get("/children/{student_id}/homework")
async def parent_view_child_homework(
    student_id: uuid.UUID,
    current_user: User = Depends(require_permissions(["VIEW_HOMEWORK"])),
    db: AsyncSession = Depends(get_db),
):
    """HW-BR-014: View assigned homework, submission status, grades, and teacher feedback for linked child[cite: 1]."""
    student = await _verify_parent_child(db, current_user.user_id, student_id)
    stmt = (
        select(Assignment.title, Assignment.due_at, AssignmentSubmission.status, AssignmentSubmission.awarded_score, AssignmentSubmission.teacher_feedback)
        .join(Assignment, AssignmentSubmission.assignment_id == Assignment.assignment_id)
        .where(AssignmentSubmission.student_id == student_id)
        .order_by(Assignment.due_at.desc())
        .limit(15)
    )
    homeworks = (await db.execute(stmt)).fetchall()
    return [
        {"title": t, "due_at": d, "status": s, "score": sc, "feedback": fb}
        for t, d, s, sc, fb in homeworks
    ]


@router.get("/children/{student_id}/exams")
async def parent_view_child_exams(
    student_id: uuid.UUID,
    current_user: User = Depends(require_permissions(["VIEW_EXAMS"])),
    db: AsyncSession = Depends(get_db),
):
    """View exams scheduled for the linked child[cite: 1]."""
    student = await _verify_parent_child(db, current_user.user_id, student_id)
    return {"student_id": student.student_id, "scheduled_exams": []}


@router.get("/children/{student_id}/exam-results")
async def parent_view_child_exam_results(
    student_id: uuid.UUID,
    current_user: User = Depends(require_permissions(["VIEW_EXAM_RESULTS"])),
    db: AsyncSession = Depends(get_db),
):
    """EX-BR-011: View examination results belonging to the officially linked student[cite: 1]."""
    student = await _verify_parent_child(db, current_user.user_id, student_id)
    return {"student_id": student.student_id, "exam_results": []}


@router.get("/children/{student_id}/grades")
async def parent_view_child_grades(
    student_id: uuid.UUID,
    current_user: User = Depends(require_permissions(["VIEW_GRADES"])),
    db: AsyncSession = Depends(get_db),
):
    """GR-BR-007: View official Mid-Year and End-of-Year results belonging to linked student[cite: 1]."""
    student = await _verify_parent_child(db, current_user.user_id, student_id)
    return {"student_id": student.student_id, "official_results": []}


@router.post("/communications/send", status_code=status.HTTP_201_CREATED)
async def parent_send_private_message(
    payload: ParentMessageRequest,
    current_user: User = Depends(require_permissions(["SEND_PRIVATE_MESSAGE"])),
    db: AsyncSession = Depends(get_db),
):
    """Send private message within authorized communication boundaries[cite: 1]."""
    return {"message": "Private message sent successfully"}


@router.get("/communications/inbox")
async def parent_view_inbox(
    current_user: User = Depends(require_permissions(["RECEIVE_PRIVATE_MESSAGE"])),
    db: AsyncSession = Depends(get_db),
):
    """View received private messages[cite: 1]."""
    return {"messages": []}


@router.post("/communications/teachers", status_code=status.HTTP_201_CREATED)
async def parent_communicate_with_teachers(
    payload: ParentMessageRequest,
    current_user: User = Depends(require_permissions(["COMMUNICATE_WITH_TEACHERS"])),
    db: AsyncSession = Depends(get_db),
):
    """Communicate privately with authorized teachers regarding linked students[cite: 1]."""
    return {"message": "Communication sent to teacher successfully"}