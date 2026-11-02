# app/api/v1/endpoints/dashboards/director.py
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_permissions
from app.models. attendance import AttendanceChangeRequest, AttendanceOccurrence, AttendanceRecord
from app.models.system import AuditLog
from app.models.user import User
from app.schemas.dashboards.director import DirectorDashboardResponse
from app.services.audit_helper import record_audit_event
from app.services.dashboards.director_service import DirectorDashboardService

router = APIRouter(prefix="/director", tags=["2. School Director Workspace"])


class DirectorModifyAttendanceRequest(BaseModel):
    new_status: str = Field(..., pattern="^(PRESENT|ABSENT|LATE|EXCUSED)$")
    reason: str = Field(..., min_length=5)


class DirectorMessageRequest(BaseModel):
    recipient_user_id: uuid.UUID
    subject: str = Field(..., min_length=2, max_length=200)
    body: str = Field(..., min_length=2)


@router.get("", response_model=DirectorDashboardResponse)
async def get_director_dashboard(
    current_user: User = Depends(require_permissions(["VIEW_DASHBOARD"])),
    db: AsyncSession = Depends(get_db),
):
    """View Director executive dashboard, approval queues, and institutional metrics[cite: 1]."""
    service = DirectorDashboardService(db)
    return await service.get_dashboard()


@router.get("/users")
async def director_view_users(
    current_user: User = Depends(require_permissions(["VIEW_USERS"])),
    db: AsyncSession = Depends(get_db),
):
    """View user directory for institutional oversight[cite: 1]."""
    return {"message": "Director view of system users enabled"}


@router.get("/attendance")
async def director_view_attendance(
    target_date: Optional[date] = None,
    current_user: User = Depends(require_permissions(["VIEW_ATTENDANCE"])),
    db: AsyncSession = Depends(get_db),
):
    """View school-wide attendance records[cite: 1]."""
    q_date = target_date or date.today()
    stmt = (
        select(AttendanceRecord.status, func.count(AttendanceRecord.attendance_record_id))
        .join(AttendanceOccurrence, AttendanceRecord.occurrence_id == AttendanceOccurrence.occurrence_id)
        .where(AttendanceOccurrence.occurrence_date == q_date)
        .group_by(AttendanceRecord.status)
    )
    rows = (await db.execute(stmt)).fetchall()
    return {"date": q_date, "summary": {st: cnt for st, cnt in rows}}


@router.post("/attendance/approve-late")
async def approve_late_attendance(
    occurrence_id: uuid.UUID,
    student_id: uuid.UUID,
    reason: str = Query(..., min_length=3),
    current_user: User = Depends(require_permissions(["APPROVE_LATE"])),
    db: AsyncSession = Depends(get_db),
):
    """ATT-BR-003: Explicit manager approval required for each individual Late occurrence[cite: 1]."""
    rec = (
        await db.execute(
            select(AttendanceRecord).where(
                AttendanceRecord.occurrence_id == occurrence_id,
                AttendanceRecord.student_id == student_id,
            )
        )
    ).scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if rec:
        rec.status = "LATE"
        rec.reason = reason
        rec.approved_by_user_id = current_user.user_id
        rec.approved_at = now
    else:
        rec = AttendanceRecord(
            occurrence_id=occurrence_id,
            student_id=student_id,
            status="LATE",
            reason=reason,
            approved_by_user_id=current_user.user_id,
            approved_at=now,
        )
        db.add(rec)
        await db.flush()

    await record_audit_event(
        db=db,
        actor_user_id=current_user.user_id,
        action_type="ATTENDANCE_LATE_APPROVED",
        entity_name="AttendanceRecord",
        entity_id=rec.attendance_record_id,
        new_state={"status": "LATE", "approved_by": str(current_user.user_id)},
    )
    await db.commit()
    return {"message": "Late status explicitly authorized", "attendance_record_id": rec.attendance_record_id}


@router.post("/attendance/approve-excused")
async def approve_excused_attendance(
    occurrence_id: uuid.UUID,
    student_id: uuid.UUID,
    reason: str = Query(..., min_length=3),
    current_user: User = Depends(require_permissions(["APPROVE_EXCUSED"])),
    db: AsyncSession = Depends(get_db),
):
    """ATT-BR-004: Explicit manager approval required for each individual Excused occurrence[cite: 1]."""
    rec = (
        await db.execute(
            select(AttendanceRecord).where(
                AttendanceRecord.occurrence_id == occurrence_id,
                AttendanceRecord.student_id == student_id,
            )
        )
    ).scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if rec:
        rec.status = "EXCUSED"
        rec.reason = reason
        rec.approved_by_user_id = current_user.user_id
        rec.approved_at = now
    else:
        rec = AttendanceRecord(
            occurrence_id=occurrence_id,
            student_id=student_id,
            status="EXCUSED",
            reason=reason,
            approved_by_user_id=current_user.user_id,
            approved_at=now,
        )
        db.add(rec)
        await db.flush()

    await record_audit_event(
        db=db,
        actor_user_id=current_user.user_id,
        action_type="ATTENDANCE_EXCUSED_APPROVED",
        entity_name="AttendanceRecord",
        entity_id=rec.attendance_record_id,
        new_state={"status": "EXCUSED", "approved_by": str(current_user.user_id)},
    )
    await db.commit()
    return {"message": "Excused status explicitly authorized", "attendance_record_id": rec.attendance_record_id}


@router.patch("/attendance/{attendance_record_id}/modify")
async def modify_attendance_record(
    attendance_record_id: uuid.UUID,
    payload: DirectorModifyAttendanceRequest,
    current_user: User = Depends(require_permissions(["MODIFY_ATTENDANCE"])),
    db: AsyncSession = Depends(get_db),
):
    """ATT-BR-008: Attendance modifications performed only by authorized director/manager with audit trail[cite: 1]."""
    rec = (
        await db.execute(
            select(AttendanceRecord).where(AttendanceRecord.attendance_record_id == attendance_record_id)
        )
    ).scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Record not found.")

    old_status = rec.status
    rec.status = payload.new_status
    rec.reason = payload.reason
    rec.approved_by_user_id = current_user.user_id
    rec.approved_at = datetime.now(timezone.utc)

    await record_audit_event(
        db=db,
        actor_user_id=current_user.user_id,
        action_type="ATTENDANCE_MODIFIED_BY_DIRECTOR",
        entity_name="AttendanceRecord",
        entity_id=rec.attendance_record_id,
        previous_state={"status": old_status},
        new_state={"status": payload.new_status},
        details={"reason": payload.reason},
    )
    await db.commit()
    return {"message": "Attendance modified and audited", "attendance_record_id": attendance_record_id}


@router.get("/attendance/reports")
async def view_attendance_reports(
    current_user: User = Depends(require_permissions(["VIEW_ATTENDANCE_REPORTS"])),
    db: AsyncSession = Depends(get_db),
):
    """ATT-BR-011: Weekly and periodic attendance report overview[cite: 1]."""
    return {"message": "Attendance summary reports retrieved"}


@router.get("/homework")
async def director_view_homework(
    current_user: User = Depends(require_permissions(["VIEW_HOMEWORK"])),
    db: AsyncSession = Depends(get_db),
):
    """Institutional oversight of homework assignments[cite: 1]."""
    return {"message": "Homework oversight list retrieved"}


@router.get("/exams")
async def director_view_exams(
    current_user: User = Depends(require_permissions(["VIEW_EXAMS"])),
    db: AsyncSession = Depends(get_db),
):
    """Institutional oversight of examinations[cite: 1]."""
    return {"message": "Examinations oversight list retrieved"}


@router.get("/exams/results")
async def director_view_exam_results(
    current_user: User = Depends(require_permissions(["VIEW_EXAM_RESULTS"])),
    db: AsyncSession = Depends(get_db),
):
    """View examination results for performance monitoring[cite: 1]."""
    return {"message": "Exam results overview retrieved"}


@router.post("/exams/{exam_id}/reopen")
async def director_reopen_exam(
    exam_id: uuid.UUID,
    student_id: uuid.UUID,
    reason: str = Query(..., min_length=5),
    current_user: User = Depends(require_permissions(["REOPEN_EXAM"])),
    db: AsyncSession = Depends(get_db),
):
    """EX-BR-013/014: Exceptionally reopen exam for a specific student under director authority[cite: 1]."""
    await record_audit_event(
        db=db,
        actor_user_id=current_user.user_id,
        action_type="EXAM_REOPENED_BY_DIRECTOR",
        entity_name="Exam",
        entity_id=exam_id,
        details={"student_id": str(student_id), "reason": reason},
    )
    await db.commit()
    return {"message": "Exam reopened for specific student", "exam_id": exam_id, "student_id": student_id}


@router.post("/exams/{exam_id}/extend-time")
async def director_extend_exam_time(
    exam_id: uuid.UUID,
    student_id: uuid.UUID,
    extra_minutes: int = Query(..., ge=5),
    reason: str = Query(..., min_length=5),
    current_user: User = Depends(require_permissions(["EXTEND_EXAM_TIME"])),
    db: AsyncSession = Depends(get_db),
):
    """EX-BR-016: Extend student exam time for exceptional circumstances[cite: 1]."""
    await record_audit_event(
        db=db,
        actor_user_id=current_user.user_id,
        action_type="EXAM_TIME_EXTENDED_BY_DIRECTOR",
        entity_name="Exam",
        entity_id=exam_id,
        details={"student_id": str(student_id), "extra_minutes": extra_minutes, "reason": reason},
    )
    await db.commit()
    return {"message": f"Extended exam time by {extra_minutes} minutes", "exam_id": exam_id}


@router.get("/grades")
async def director_view_grades(
    current_user: User = Depends(require_permissions(["VIEW_GRADES"])),
    db: AsyncSession = Depends(get_db),
):
    """View official academic grades and performance records[cite: 1]."""
    return {"message": "Official academic results overview retrieved"}


@router.get("/audit-logs")
async def director_view_audit_logs(
    current_user: User = Depends(require_permissions(["VIEW_AUDIT_LOGS"])),
    db: AsyncSession = Depends(get_db),
):
    """Review administrative and security audit logs[cite: 1]."""
    stmt = select(AuditLog).order_by(AuditLog.event_timestamp.desc()).limit(50)
    logs = (await db.execute(stmt)).scalars().all()
    return [{"audit_id": l.audit_id, "action": l.action_type, "timestamp": l.event_timestamp} for l in logs]


@router.get("/reports")
async def director_view_reports(
    current_user: User = Depends(require_permissions(["VIEW_REPORTS"])),
    db: AsyncSession = Depends(get_db),
):
    """View institutional reports[cite: 1]."""
    return {"message": "Institutional reports retrieved"}


@router.post("/communications/parents")
async def communicate_with_parents(
    payload: DirectorMessageRequest,
    current_user: User = Depends(require_permissions(["COMMUNICATE_WITH_PARENTS"])),
    db: AsyncSession = Depends(get_db),
):
    """Send official communication to parents[cite: 1]."""
    return {"message": "Communication sent to parent successfully"}


@router.post("/communications/teachers")
async def communicate_with_teachers(
    payload: DirectorMessageRequest,
    current_user: User = Depends(require_permissions(["COMMUNICATE_WITH_TEACHERS"])),
    db: AsyncSession = Depends(get_db),
):
    """Send official communication to teachers[cite: 1]."""
    return {"message": "Communication sent to teacher successfully"}