# app/api/v1/endpoints/dashboards/supervisor.py
import uuid
from datetime import date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_permissions
from app.models.attendance import (
    AttendanceChangeRequest,
    AttendanceOccurrence,
    AttendanceRecord,
)
from app.models.stakeholder import StaffMember, Student
from app.models.user import User
from app.schemas.dashboards.supervisor import (
    SupervisorChangeRequestCreate,
    SupervisorDashboardResponse,
)
from app.services.audit_helper import record_audit_event
from app.services.dashboards.supervisor_service import SupervisorDashboardService

router = APIRouter(
    prefix="/supervisor",
    tags=["3. Floor Supervisor Workspace (Attendance & Absence Only)"],
)


# ==============================================================================
# Request Schemas for Floor Supervisor Operations
# ==============================================================================
class SupervisorStudentAttendanceItem(BaseModel):
    student_id: uuid.UUID
    status: str = Field(
        ...,
        pattern="^(PRESENT|ABSENT)$",
        description=(
            "ADM-FS-BR-006/009/010: Floor Supervisors record PRESENT or ABSENT. "
            "LATE and EXCUSED require explicit Director approval per occurrence."
        ),
    )
    reason: Optional[str] = None


class SupervisorRecordAttendancePayload(BaseModel):
    academic_year_id: uuid.UUID
    class_id: uuid.UUID
    occurrence_date: date
    period_number: Optional[int] = Field(default=1, ge=1)
    subject_id: Optional[uuid.UUID] = None
    records: List[SupervisorStudentAttendanceItem]


# ==============================================================================
# Helper: Verify Active Floor Supervisor Profile (ADM-FS-BR-003, ADM-FS-BR-004)
# ==============================================================================
async def _get_verified_supervisor(db: AsyncSession, current_user: User) -> StaffMember:
    staff = (
        await db.execute(
            select(StaffMember).where(
                StaffMember.user_id == current_user.user_id,
                StaffMember.is_active.is_(True),
            )
        )
    ).scalar_one_or_none()
    if not staff or staff.staff_type not in ("FLOOR_SUPERVISOR", "ADMIN_STAFF", "DIRECTOR"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Active Floor Supervisor staff profile required (ADM-FS-BR-003).",
        )
    return staff


# ==============================================================================
# 1. Dashboard Overview (VIEW_DASHBOARD)
# ==============================================================================
@router.get("", response_model=SupervisorDashboardResponse)
async def get_supervisor_dashboard(
    current_user: User = Depends(require_permissions(["VIEW_DASHBOARD"])),
    db: AsyncSession = Depends(get_db),
):
    """
    ADM-FS-BR-019: Attendance-focused dashboard containing only authorized attendance
    information. Zero academic, exam, homework, or user-management exposure.
    """
    await _get_verified_supervisor(db, current_user)
    service = SupervisorDashboardService(db)
    return await service.get_dashboard(current_user)


# ==============================================================================
# 2. View, Search & Filter Attendance Within Scope (VIEW_ATTENDANCE)
# ==============================================================================
@router.get("/attendance")
async def view_scoped_attendance_records(
    class_id: Optional[uuid.UUID] = Query(None, description="Filter by assigned class_id"),
    student_id: Optional[uuid.UUID] = Query(None, description="Search specific student_id"),
    occurrence_date: Optional[date] = Query(None, description="Filter by date (defaults to today)"),
    status_filter: Optional[str] = Query(None, pattern="^(PRESENT|ABSENT|LATE|EXCUSED)$"),
    limit: int = Query(100, le=500),
    current_user: User = Depends(require_permissions(["VIEW_ATTENDANCE"])),
    db: AsyncSession = Depends(get_db),
):
    """
    04.5.5 Section 6 & ADM-FS-BR-005:
    View, search, and filter assigned students' attendance records within authorized scope.
    """
    await _get_verified_supervisor(db, current_user)

    stmt = (
        select(
            AttendanceRecord.attendance_record_id,
            AttendanceRecord.occurrence_id,
            AttendanceRecord.student_id,
            Student.student_code,
            Student.first_name,
            Student.last_name,
            AttendanceOccurrence.class_id,
            AttendanceOccurrence.occurrence_date,
            AttendanceOccurrence.period_number,
            AttendanceRecord.status,
            AttendanceRecord.reason,
            AttendanceRecord.approved_by_user_id,
        )
        .join(AttendanceOccurrence, AttendanceRecord.occurrence_id == AttendanceOccurrence.occurrence_id)
        .join(Student, AttendanceRecord.student_id == Student.student_id)
        .order_by(AttendanceOccurrence.occurrence_date.desc(), Student.student_code.asc())
        .limit(limit)
    )

    if class_id:
        stmt = stmt.where(AttendanceOccurrence.class_id == class_id)
    if student_id:
        stmt = stmt.where(AttendanceRecord.student_id == student_id)
    if occurrence_date:
        stmt = stmt.where(AttendanceOccurrence.occurrence_date == occurrence_date)
    if status_filter:
        stmt = stmt.where(AttendanceRecord.status == status_filter)

    rows = (await db.execute(stmt)).fetchall()
    return [
        {
            "attendance_record_id": r.attendance_record_id,
            "occurrence_id": r.occurrence_id,
            "student_id": r.student_id,
            "student_code": r.student_code,
            "student_name": f"{r.first_name} {r.last_name}",
            "class_id": r.class_id,
            "occurrence_date": r.occurrence_date,
            "period_number": r.period_number,
            "status": r.status,
            "reason": r.reason,
            "approved_by_user_id": r.approved_by_user_id,
        }
        for r in rows
    ]


# ==============================================================================
# 3. Record Daily Attendance & Report Attendance Issues (RECORD_ATTENDANCE)
# ==============================================================================
@router.post("/attendance/record", status_code=status.HTTP_201_CREATED)
async def record_daily_attendance(
    payload: SupervisorRecordAttendancePayload,
    current_user: User = Depends(require_permissions(["RECORD_ATTENDANCE"])),
    db: AsyncSession = Depends(get_db),
):
    """
    ATT-BR-001, ADM-FS-BR-006, ADM-FS-BR-007, ADM-FS-BR-008:
    - Floor Supervisor records daily Present / Absent status.
    - Cannot modify or overwrite an existing attendance record once recorded (ADM-FS-BR-007).
    - Records the activity in the Audit Log (04.5.5 Section 7).
    """
    await _get_verified_supervisor(db, current_user)

    # Check if occurrence already exists for (class_id, occurrence_date, period_number, subject_id)
    occ_stmt = select(AttendanceOccurrence).where(
        AttendanceOccurrence.class_id == payload.class_id,
        AttendanceOccurrence.occurrence_date == payload.occurrence_date,
        AttendanceOccurrence.period_number == payload.period_number,
        AttendanceOccurrence.subject_id == payload.subject_id,
    )
    occurrence = (await db.execute(occ_stmt)).scalar_one_or_none()

    if not occurrence:
        occurrence = AttendanceOccurrence(
            academic_year_id=payload.academic_year_id,
            class_id=payload.class_id,
            subject_id=payload.subject_id,
            occurrence_date=payload.occurrence_date,
            period_number=payload.period_number,
            recorded_by_user_id=current_user.user_id,
        )
        db.add(occurrence)
        await db.flush()

    created_records_count = 0
    for item in payload.records:
        # Enforce ADM-FS-BR-007: Floor Supervisor cannot modify attendance after it has been recorded
        existing_rec = (
            await db.execute(
                select(AttendanceRecord).where(
                    AttendanceRecord.occurrence_id == occurrence.occurrence_id,
                    AttendanceRecord.student_id == item.student_id,
                )
            )
        ).scalar_one_or_none()

        if existing_rec:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Attendance for student {item.student_id} is already recorded as '{existing_rec.status}'. "
                    "Floor Supervisors cannot modify recorded attendance (ADM-FS-BR-007). "
                    "Use POST /supervisor/attendance/report-issue to request Director modification."
                ),
            )

        new_rec = AttendanceRecord(
            occurrence_id=occurrence.occurrence_id,
            student_id=item.student_id,
            status=item.status,  # Strictly PRESENT or ABSENT
            reason=item.reason,
            approved_by_user_id=None,
            approved_at=None,
        )
        db.add(new_rec)
        created_records_count += 1

    await record_audit_event(
        db=db,
        actor_user_id=current_user.user_id,
        action_type="DAILY_ATTENDANCE_RECORDED",
        entity_name="AttendanceOccurrence",
        entity_id=occurrence.occurrence_id,
        new_state={
            "class_id": str(payload.class_id),
            "occurrence_date": payload.occurrence_date.isoformat(),
            "students_recorded": created_records_count,
        },
    )
    await db.commit()

    return {
        "message": "Daily attendance recorded and audited (ADM-FS-BR-006)",
        "occurrence_id": occurrence.occurrence_id,
        "students_recorded": created_records_count,
    }


@router.post("/attendance/report-issue", status_code=status.HTTP_201_CREATED)
async def report_attendance_issue_to_director(
    payload: SupervisorChangeRequestCreate,
    current_user: User = Depends(require_permissions(["RECORD_ATTENDANCE"])),
    db: AsyncSession = Depends(get_db),
):
    """
    04.5.5 Section 6 ("Report attendance-related issues") & ADM-FS-BR-007 to 011:
    Floor Supervisors cannot directly modify recorded attendance or approve LATE/EXCUSED.
    Instead, they submit an AttendanceChangeRequest for the Director/Authorized Manager to review.
    """
    await _get_verified_supervisor(db, current_user)

    rec = (
        await db.execute(
            select(AttendanceRecord).where(
                AttendanceRecord.attendance_record_id == payload.attendance_record_id
            )
        )
    ).scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Attendance record not found.")

    if rec.status == payload.new_status:
        raise HTTPException(
            status_code=400,
            detail="Requested new status must differ from the current recorded status (chk_status_differ).",
        )

    change_req = AttendanceChangeRequest(
        attendance_record_id=rec.attendance_record_id,
        requested_by_user_id=current_user.user_id,
        old_status=rec.status,
        new_status=payload.new_status,
        reason=payload.reason,
        request_status="PENDING",
    )
    db.add(change_req)
    await db.flush()

    await record_audit_event(
        db=db,
        actor_user_id=current_user.user_id,
        action_type="ATTENDANCE_CHANGE_OR_EXCEPTION_REQUESTED",
        entity_name="AttendanceChangeRequest",
        entity_id=change_req.request_id,
        previous_state={"status": rec.status},
        new_state={"requested_status": payload.new_status, "request_status": "PENDING"},
        details={"reason": payload.reason, "attendance_record_id": str(rec.attendance_record_id)},
    )
    await db.commit()

    return {
        "message": "Attendance issue / exception request routed to Director for approval (ADM-FS-BR-011)",
        "request_id": change_req.request_id,
        "old_status": rec.status,
        "requested_new_status": payload.new_status,
        "request_status": change_req.request_status,
    }


# ==============================================================================
# 4. View Weekly Attendance Reports (VIEW_ATTENDANCE_REPORTS)
# ==============================================================================
@router.get("/attendance/reports/weekly")
async def view_weekly_attendance_report(
    class_id: Optional[uuid.UUID] = Query(None, description="Filter report by assigned class_id"),
    week_start: Optional[date] = Query(None, description="Start date of the 7-day week"),
    current_user: User = Depends(require_permissions(["VIEW_ATTENDANCE_REPORTS"])),
    db: AsyncSession = Depends(get_db),
):
    """
    ATT-BR-011 & 04.5.5 Section 6 ("View attendance reports"):
    Summarizes student attendance during the selected week within the supervisor's scope.
    """
    await _get_verified_supervisor(db, current_user)

    start_date = week_start or (date.today() - timedelta(days=6))
    end_date = start_date + timedelta(days=6)

    stmt = (
        select(
            AttendanceOccurrence.occurrence_date,
            AttendanceRecord.status,
            func.count(AttendanceRecord.attendance_record_id),
        )
        .join(AttendanceOccurrence, AttendanceRecord.occurrence_id == AttendanceOccurrence.occurrence_id)
        .where(
            AttendanceOccurrence.occurrence_date >= start_date,
            AttendanceOccurrence.occurrence_date <= end_date,
        )
        .group_by(AttendanceOccurrence.occurrence_date, AttendanceRecord.status)
        .order_by(AttendanceOccurrence.occurrence_date.asc())
    )
    if class_id:
        stmt = stmt.where(AttendanceOccurrence.class_id == class_id)

    rows = (await db.execute(stmt)).fetchall()
    daily_breakdown = {}
    totals = {"PRESENT": 0, "ABSENT": 0, "LATE": 0, "EXCUSED": 0}

    for occ_date, st, cnt in rows:
        day_key = occ_date.isoformat()
        if day_key not in daily_breakdown:
            daily_breakdown[day_key] = {"PRESENT": 0, "ABSENT": 0, "LATE": 0, "EXCUSED": 0}
        if st in daily_breakdown[day_key]:
            daily_breakdown[day_key][st] = cnt
            totals[st] += cnt

    return {
        "week_start": start_date,
        "week_end": end_date,
        "class_id_filter": class_id,
        "weekly_totals": totals,
        "daily_breakdown": daily_breakdown,
    }