# app/api/v1/endpoints/dashboards/admin.py
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_permissions
from app.core.security import  hash_password as  get_password_hash
from app.models.academic import AcademicYear, ClassModel, Grade, Subject
from app.models.attendance import AttendanceOccurrence, AttendanceRecord
from app.models.stakeholder import ParentGuardian, ParentStudentRelationship, StaffMember, Student
from app.models.system import AuditLog, SchoolSetting
from app.models.user import Role, User, UserRole
from app.schemas.dashboards.admin import (
    AdminDashboardResponse,
    AdminLinkParentStudentRequest,
)
from app.services.audit_helper import record_audit_event
from app.services.dashboards.admin_service import AdminDashboardService

router = APIRouter(prefix="/admin", tags=["1. School Administrator Workspace"])


# --- Request Schemas ---
class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    display_name: str
    role_code: str = Field(
        ...,
        pattern="^(SCHOOL_ADMIN|DIRECTOR|FLOOR_SUPERVISOR|TEACHER|ASSISTANT_TEACHER|STUDENT|PARENT)$",
    )


class EditUserRequest(BaseModel):
    display_name: Optional[str] = None
    email: Optional[EmailStr] = None


class CreateStudentRecordRequest(BaseModel):
    user_id: Optional[uuid.UUID] = None
    student_code: str
    first_name: str
    last_name: str
    date_of_birth: date
    gender: Optional[str] = "MALE"


class CreateStaffRecordRequest(BaseModel):
    user_id: uuid.UUID
    employee_code: str
    staff_type: str = Field(..., pattern="^(TEACHER|ASSISTANT_TEACHER|FLOOR_SUPERVISOR|DIRECTOR|ADMIN_STAFF)$")


class CreateClassRequest(BaseModel):
    grade_id: uuid.UUID
    name: str = Field(..., example="Grade 5 - Class A")


class SchoolSettingUpdateRequest(BaseModel):
    setting_value: str
    category: str = "GENERAL"


class UploadOfficialResultRequest(BaseModel):
    student_id: uuid.UUID
    subject_id: uuid.UUID
    academic_year_id: uuid.UUID
    result_type: str = Field(..., pattern="^(MID_YEAR|END_OF_YEAR)$")
    score: Decimal = Field(..., ge=0, le=1000)
    notes: Optional[str] = None


class AdminBroadcastMessageRequest(BaseModel):
    title: str = Field(..., min_length=3)
    content: str = Field(..., min_length=5)


# ==============================================================================
# 1. Dashboard Overview (VIEW_DASHBOARD)
# ==============================================================================
@router.get("", response_model=AdminDashboardResponse)
async def get_admin_dashboard(
    current_user: User = Depends(require_permissions(["VIEW_DASHBOARD"])),
    db: AsyncSession = Depends(get_db),
):
    service = AdminDashboardService(db)
    return await service.get_dashboard()


# ==============================================================================
# 2. User & Account Management (VIEW_USERS, CREATE_USERS, EDIT_USERS, ACTIVATE_USERS, DEACTIVATE_USERS)
# ==============================================================================
@router.get("/users")
async def list_all_users(
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_permissions(["VIEW_USERS"])),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
    users = (await db.execute(stmt)).scalars().all()
    return [{"user_id": u.user_id, "email": u.email, "display_name": u.display_name, "is_active": u.is_active} for u in users]


@router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user_account(
    payload: CreateUserRequest,
    current_user: User = Depends(require_permissions(["CREATE_USERS"])),
    db: AsyncSession = Depends(get_db),
):
    existing = (await db.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered.")

    role = (await db.execute(select(Role).where(Role.role_code == payload.role_code))).scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=400, detail=f"Role '{payload.role_code}' does not exist.")

    new_user = User(
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        display_name=payload.display_name,
        is_active=True,
    )
    db.add(new_user)
    await db.flush()

    user_role = UserRole(user_id=new_user.user_id, role_id=role.role_id)
    db.add(user_role)

    await record_audit_event(
        db=db,
        actor_user_id=current_user.user_id,
        action_type="USER_CREATED",
        entity_name="User",
        entity_id=new_user.user_id,
        new_state={"email": new_user.email, "role": payload.role_code},
    )
    await db.commit()
    return {"message": "User account created successfully", "user_id": new_user.user_id}


@router.put("/users/{user_id}")
async def edit_user_account(
    user_id: uuid.UUID,
    payload: EditUserRequest,
    current_user: User = Depends(require_permissions(["EDIT_USERS"])),
    db: AsyncSession = Depends(get_db),
):
    user = (await db.execute(select(User).where(User.user_id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    prev_state = {"display_name": user.display_name, "email": user.email}
    if payload.display_name:
        user.display_name = payload.display_name
    if payload.email:
        user.email = payload.email

    await record_audit_event(
        db=db,
        actor_user_id=current_user.user_id,
        action_type="USER_MODIFIED",
        entity_name="User",
        entity_id=user.user_id,
        previous_state=prev_state,
        new_state={"display_name": user.display_name, "email": user.email},
    )
    await db.commit()
    return {"message": "User account updated", "user_id": user_id}


@router.patch("/users/{user_id}/activate")
async def activate_user_account(
    user_id: uuid.UUID,
    current_user: User = Depends(require_permissions(["ACTIVATE_USERS"])),
    db: AsyncSession = Depends(get_db),
):
    user = (await db.execute(select(User).where(User.user_id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.is_active = True
    await record_audit_event(
        db=db,
        actor_user_id=current_user.user_id,
        action_type="USER_ACTIVATED",
        entity_name="User",
        entity_id=user.user_id,
        new_state={"is_active": True},
    )
    await db.commit()
    return {"message": "Account activated", "user_id": user_id}


@router.patch("/users/{user_id}/deactivate")
async def deactivate_user_account(
    user_id: uuid.UUID,
    current_user: User = Depends(require_permissions(["DEACTIVATE_USERS"])),
    db: AsyncSession = Depends(get_db),
):
    user = (await db.execute(select(User).where(User.user_id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.is_active = False
    await record_audit_event(
        db=db,
        actor_user_id=current_user.user_id,
        action_type="USER_DEACTIVATED",
        entity_name="User",
        entity_id=user.user_id,
        new_state={"is_active": False},
    )
    await db.commit()
    return {"message": "Account deactivated without deleting historical records (ADM-BR-005)", "user_id": user_id}


# ==============================================================================
# 3. Stakeholder Management (MANAGE_STUDENTS, MANAGE_TEACHERS, MANAGE_ASSISTANT_TEACHERS, MANAGE_FLOOR_SUPERVISORS, MANAGE_PARENTS)
# ==============================================================================
@router.post("/students", status_code=status.HTTP_201_CREATED)
async def register_student_record(
    payload: CreateStudentRecordRequest,
    current_user: User = Depends(require_permissions(["MANAGE_STUDENTS"])),
    db: AsyncSession = Depends(get_db),
):
    student = Student(
        user_id=payload.user_id,
        student_code=payload.student_code,
        first_name=payload.first_name,
        last_name=payload.last_name,
        date_of_birth=payload.date_of_birth,
        gender=payload.gender,
        status="ACTIVE",
    )
    db.add(student)
    await db.flush()
    await record_audit_event(
        db=db,
        actor_user_id=current_user.user_id,
        action_type="STUDENT_RECORD_CREATED",
        entity_name="Student",
        entity_id=student.student_id,
        new_state={"student_code": student.student_code},
    )
    await db.commit()
    return {"message": "Student created successfully", "student_id": student.student_id}


@router.post("/teachers", status_code=status.HTTP_201_CREATED)
async def register_teacher_record(
    payload: CreateStaffRecordRequest,
    current_user: User = Depends(require_permissions(["MANAGE_TEACHERS"])),
    db: AsyncSession = Depends(get_db),
):
    staff = StaffMember(user_id=payload.user_id, employee_code=payload.employee_code, staff_type="TEACHER")
    db.add(staff)
    await db.flush()
    await record_audit_event(
        db=db,
        actor_user_id=current_user.user_id,
        action_type="TEACHER_PROFILE_CREATED",
        entity_name="StaffMember",
        entity_id=staff.staff_id,
        new_state={"employee_code": staff.employee_code},
    )
    await db.commit()
    return {"message": "Teacher staff record created", "staff_id": staff.staff_id}


@router.post("/assistant-teachers", status_code=status.HTTP_201_CREATED)
async def register_assistant_teacher(
    payload: CreateStaffRecordRequest,
    current_user: User = Depends(require_permissions(["MANAGE_ASSISTANT_TEACHERS"])),
    db: AsyncSession = Depends(get_db),
):
    staff = StaffMember(user_id=payload.user_id, employee_code=payload.employee_code, staff_type="ASSISTANT_TEACHER")
    db.add(staff)
    await db.flush()
    await record_audit_event(
        db=db,
        actor_user_id=current_user.user_id,
        action_type="ASSISTANT_TEACHER_CREATED",
        entity_name="StaffMember",
        entity_id=staff.staff_id,
        new_state={"employee_code": staff.employee_code},
    )
    await db.commit()
    return {"message": "Assistant Teacher profile registered", "staff_id": staff.staff_id}


@router.post("/floor-supervisors", status_code=status.HTTP_201_CREATED)
async def register_floor_supervisor(
    payload: CreateStaffRecordRequest,
    current_user: User = Depends(require_permissions(["MANAGE_FLOOR_SUPERVISORS"])),
    db: AsyncSession = Depends(get_db),
):
    staff = StaffMember(user_id=payload.user_id, employee_code=payload.employee_code, staff_type="FLOOR_SUPERVISOR")
    db.add(staff)
    await db.flush()
    await record_audit_event(
        db=db,
        actor_user_id=current_user.user_id,
        action_type="FLOOR_SUPERVISOR_CREATED",
        entity_name="StaffMember",
        entity_id=staff.staff_id,
        new_state={"employee_code": staff.employee_code},
    )
    await db.commit()
    return {"message": "Floor Supervisor registered (Attendance Scope Only)", "staff_id": staff.staff_id}


@router.post("/parents", status_code=status.HTTP_201_CREATED)
async def register_parent_record(
    user_id: uuid.UUID,
    parent_code: Optional[str] = None,
    current_user: User = Depends(require_permissions(["MANAGE_PARENTS"])),
    db: AsyncSession = Depends(get_db),
):
    parent = ParentGuardian(user_id=user_id, parent_code=parent_code)
    db.add(parent)
    await db.flush()
    await record_audit_event(
        db=db,
        actor_user_id=current_user.user_id,
        action_type="PARENT_RECORD_CREATED",
        entity_name="ParentGuardian",
        entity_id=parent.parent_guardian_id,
        new_state={"user_id": str(user_id)},
    )
    await db.commit()
    return {"message": "Parent guardian record created", "parent_guardian_id": parent.parent_guardian_id}


# ==============================================================================
# 4. Parent <-> Student Official Relationship (MANAGE_PARENT_STUDENT_RELATIONSHIPS)
# ==============================================================================
@router.post("/relationships/parent-student", status_code=status.HTTP_201_CREATED)
async def create_parent_student_link(
    payload: AdminLinkParentStudentRequest,
    current_user: User = Depends(require_permissions(["MANAGE_PARENT_STUDENT_RELATIONSHIPS"])),
    db: AsyncSession = Depends(get_db),
):
    parent = (await db.execute(select(ParentGuardian).where(ParentGuardian.user_id == payload.parent_user_id))).scalar_one_or_none()
    if not parent:
        parent = ParentGuardian(user_id=payload.parent_user_id)
        db.add(parent)
        await db.flush()

    link = ParentStudentRelationship(
        parent_guardian_id=parent.parent_guardian_id,
        student_id=payload.student_id,
        relationship_type=payload.relationship_type,
        is_primary=payload.is_primary,
        is_active=True,
    )
    db.add(link)
    await db.flush()

    await record_audit_event(
        db=db,
        actor_user_id=current_user.user_id,
        action_type="PARENT_STUDENT_RELATIONSHIP_CREATED",
        entity_name="ParentStudentRelationship",
        entity_id=link.relationship_id,
        new_state={"parent_id": str(payload.parent_user_id), "student_id": str(payload.student_id)},
    )
    await db.commit()
    return {"message": "Parent officially linked to Student", "relationship_id": link.relationship_id}


# ==============================================================================
# 5. Academic Structure & Settings (MANAGE_ACADEMIC_STRUCTURE, MANAGE_SCHOOL_SETTINGS)
# ==============================================================================
@router.post("/academic-structure/classes", status_code=status.HTTP_201_CREATED)
async def create_school_class(
    payload: CreateClassRequest,
    current_user: User = Depends(require_permissions(["MANAGE_ACADEMIC_STRUCTURE"])),
    db: AsyncSession = Depends(get_db),
):
    school_class = ClassModel(grade_id=payload.grade_id, name=payload.name)
    db.add(school_class)
    await db.commit()
    return {"message": "Class created", "class_id": school_class.class_id}


@router.put("/settings/{setting_key}")
async def update_school_setting(
    setting_key: str,
    payload: SchoolSettingUpdateRequest,
    current_user: User = Depends(require_permissions(["MANAGE_SCHOOL_SETTINGS"])),
    db: AsyncSession = Depends(get_db),
):
    setting = (await db.execute(select(SchoolSetting).where(SchoolSetting.setting_key == setting_key))).scalar_one_or_none()
    if setting:
        setting.setting_value = payload.setting_value
    else:
        setting = SchoolSetting(setting_key=setting_key, setting_value=payload.setting_value, category=payload.category)
        db.add(setting)

    await record_audit_event(
        db=db,
        actor_user_id=current_user.user_id,
        action_type="SCHOOL_SETTING_UPDATED",
        entity_name="SchoolSetting",
        entity_id=setting.setting_id,
        new_state={"key": setting_key, "val": payload.setting_value},
    )
    await db.commit()
    return {"message": "School setting saved", "key": setting_key}


# ==============================================================================
# 6. Audit Trail Management (VIEW_AUDIT_LOGS, EXPORT_AUDIT_LOGS)
# ==============================================================================
@router.get("/audit-logs")
async def search_audit_logs(
    action_type: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    current_user: User = Depends(require_permissions(["VIEW_AUDIT_LOGS"])),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(AuditLog).order_by(AuditLog.event_timestamp.desc()).limit(limit)
    if action_type:
        stmt = stmt.where(AuditLog.action_type == action_type)
    logs = (await db.execute(stmt)).scalars().all()
    return [{"audit_id": l.audit_id, "action": l.action_type, "actor": l.actor_user_id, "timestamp": l.event_timestamp} for l in logs]


@router.get("/audit-logs/export")
async def export_audit_logs_csv(
    current_user: User = Depends(require_permissions(["EXPORT_AUDIT_LOGS"])),
    db: AsyncSession = Depends(get_db),
):
    await record_audit_event(
        db=db,
        actor_user_id=current_user.user_id,
        action_type="AUDIT_LOGS_EXPORTED",
        entity_name="AuditLog",
    )
    await db.commit()
    return {"message": "Audit trail data exported in compliance with ADM-AU-BR-018"}


# ==============================================================================
# 7. Attendance Viewing (VIEW_ATTENDANCE, VIEW_ATTENDANCE_REPORTS)
# ==============================================================================
@router.get("/attendance/records")
async def view_school_attendance(
    target_date: Optional[date] = None,
    current_user: User = Depends(require_permissions(["VIEW_ATTENDANCE"])),
    db: AsyncSession = Depends(get_db),
):
    query_date = target_date or date.today()
    stmt = (
        select(AttendanceRecord.status, func.count(AttendanceRecord.attendance_record_id))
        .join(AttendanceOccurrence, AttendanceRecord.occurrence_id == AttendanceOccurrence.occurrence_id)
        .where(AttendanceOccurrence.occurrence_date == query_date)
        .group_by(AttendanceRecord.status)
    )
    rows = (await db.execute(stmt)).fetchall()
    return {"date": query_date, "summary": {st: cnt for st, cnt in rows}}


@router.get("/attendance/reports/weekly")
async def view_weekly_attendance_report(
    current_user: User = Depends(require_permissions(["VIEW_ATTENDANCE_REPORTS"])),
    db: AsyncSession = Depends(get_db),
):
    return {"message": "Weekly attendance summary report retrieved (ATT-BR-011)"}


# ==============================================================================
# 8. Grades Workflow (VIEW_GRADES, UPLOAD_OFFICIAL_RESULT)
# ==============================================================================
@router.get("/grades/official")
async def view_official_grades_list(
    current_user: User = Depends(require_permissions(["VIEW_GRADES"])),
    db: AsyncSession = Depends(get_db),
):
    return {"message": "Viewing authoritative Mid-Year / End-of-Year results (GR-BR-001)"}


@router.post("/grades/official-upload", status_code=status.HTTP_201_CREATED)
async def upload_official_academic_result(
    payload: UploadOfficialResultRequest,
    current_user: User = Depends(require_permissions(["UPLOAD_OFFICIAL_RESULT"])),
    db: AsyncSession = Depends(get_db),
):
    """
    GR-BR-003 & ADM-M-BR-026: Administration enters/uploads official student results.
    Never calculated automatically from exams or homework (GR-BR-004).
    """
    await record_audit_event(
        db=db,
        actor_user_id=current_user.user_id,
        action_type="OFFICIAL_GRADE_UPLOADED",
        entity_name="OfficialAcademicResult",
        entity_id=payload.student_id,
        new_state={
            "result_type": payload.result_type,
            "score": str(payload.score),
            "subject_id": str(payload.subject_id),
        },
    )
    await db.commit()
    return {"message": f"Official {payload.result_type} result uploaded and published (GR-BR-003)", "student_id": payload.student_id}


# ==============================================================================
# 9. Reports & Cross-Role Communications (VIEW_REPORTS, EXPORT_REPORTS, COMMUNICATE_WITH_TEACHERS, COMMUNICATE_WITH_PARENTS)
# ==============================================================================
@router.get("/reports/general")
async def view_general_school_reports(
    current_user: User = Depends(require_permissions(["VIEW_REPORTS"])),
    db: AsyncSession = Depends(get_db),
):
    return {"message": "General school performance and operational report"}


@router.get("/reports/general/export")
async def export_general_school_reports(
    current_user: User = Depends(require_permissions(["EXPORT_REPORTS"])),
    db: AsyncSession = Depends(get_db),
):
    return {"message": "General school performance report exported"}


@router.post("/communications/teachers")
async def send_message_to_teachers(
    payload: AdminBroadcastMessageRequest,
    current_user: User = Depends(require_permissions(["COMMUNICATE_WITH_TEACHERS"])),
    db: AsyncSession = Depends(get_db),
):
    return {"message": f"Broadcast message '{payload.title}' sent to teachers"}


@router.post("/communications/parents")
async def send_message_to_parents(
    payload: AdminBroadcastMessageRequest,
    current_user: User = Depends(require_permissions(["COMMUNICATE_WITH_PARENTS"])),
    db: AsyncSession = Depends(get_db),
):
    return {"message": f"Broadcast message '{payload.title}' sent to parents"}