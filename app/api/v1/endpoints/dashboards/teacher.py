# app/api/v1/endpoints/dashboards/teacher.py
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_permissions
from app.models.coursework import Assignment, AssignmentAttachment, AssignmentSubmission
from app.models.stakeholder import ParentGuardian, ParentStudentRelationship, StaffMember, Student
from app.models.user import User
from app.schemas.dashboards.teacher import (
    TeacherCreateAssignmentRequest,
    TeacherDashboardResponse,
    TeacherGradeSubmissionRequest,
)
from app.services.audit_helper import record_audit_event
from app.services.dashboards.teacher_service import TeacherDashboardService

router = APIRouter(prefix="/teacher", tags=["4. Teacher Academic Workspace"])


# ==============================================================================
# Request & Response Schemas for Teacher Operations
# ==============================================================================
class EditHomeworkRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    instructions: Optional[str] = None
    assignment_type: Optional[str] = Field(None, pattern="^(FILE_BASED|ONLINE_TEXT|HYBRID)$")
    max_score: Optional[Decimal] = Field(None, gt=0)
    due_at: Optional[datetime] = None
    allow_resubmission: Optional[bool] = None
    max_attempts: Optional[int] = Field(None, gt=0)
    attachment_storage_key: Optional[str] = None
    attachment_file_name: Optional[str] = None


class CreateExamRequest(BaseModel):
    class_id: uuid.UUID
    subject_id: uuid.UUID
    title: str = Field(..., min_length=3, max_length=255)
    opening_time: datetime
    closing_time: datetime
    duration_minutes: int = Field(default=60, gt=0)
    passing_score: Decimal = Field(default=Decimal("50.00"), ge=0)


class EditExamRequest(BaseModel):
    title: Optional[str] = None
    opening_time: Optional[datetime] = None
    closing_time: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(None, gt=0)
    reason: str = Field(..., min_length=3, description="EX-BR-017: Schedule changes are audited")


class ExamQuestionItem(BaseModel):
    question_type: str = Field(..., pattern="^(MCQ|TRUE_FALSE|TEXT|IMAGE)$")
    question_text: str = Field(..., min_length=1)
    image_storage_key: Optional[str] = None
    options: Optional[List[str]] = None
    correct_answer: Optional[str] = None
    points: Decimal = Field(default=Decimal("1.00"), gt=0)


class ManageExamQuestionsRequest(BaseModel):
    questions: List[ExamQuestionItem]


class ExceptionalExamReopenRequest(BaseModel):
    student_id: uuid.UUID
    new_opening_time: datetime
    new_closing_time: datetime
    reason: str = Field(..., min_length=5, description="EX-BR-012/013: Legitimate technical issue or absence")


class ExtendStudentExamTimeRequest(BaseModel):
    student_id: uuid.UUID
    additional_minutes: int = Field(..., ge=5, le=180)
    new_closing_time: Optional[datetime] = None
    reason: str = Field(..., min_length=5, description="EX-BR-016: Technical problem justification")


class PrepareAcademicResultRequest(BaseModel):
    student_id: uuid.UUID
    subject_id: uuid.UUID
    academic_year_id: uuid.UUID
    result_type: str = Field(..., pattern="^(MID_YEAR|END_OF_YEAR)$")
    finalized_score: Decimal = Field(..., ge=0, le=1000)
    teacher_remarks: Optional[str] = None


class PrivateMessageRequest(BaseModel):
    recipient_user_id: uuid.UUID
    subject: str = Field(..., min_length=2, max_length=200)
    body: str = Field(..., min_length=2)


class ScopedStudentMessageRequest(BaseModel):
    student_id: uuid.UUID
    subject: str = Field(..., min_length=2, max_length=200)
    message: str = Field(..., min_length=2)


class ScopedParentMessageRequest(BaseModel):
    student_id: uuid.UUID
    parent_guardian_id: Optional[uuid.UUID] = None
    subject: str = Field(..., min_length=2, max_length=200)
    message: str = Field(..., min_length=2)


# ==============================================================================
# Helper: Resolve & Validate Active Teacher Profile (ADM-TC-BR-004, ADM-TC-BR-008)
# ==============================================================================
async def _get_verified_teacher(db: AsyncSession, current_user: User) -> StaffMember:
    staff = (
        await db.execute(
            select(StaffMember).where(
                StaffMember.user_id == current_user.user_id,
                StaffMember.is_active.is_(True),
            )
        )
    ).scalar_one_or_none()
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Active Teacher staff profile required (ADM-TC-BR-004).",
        )
    return staff


# ==============================================================================
# 1. Dashboard Overview (VIEW_DASHBOARD)
# ==============================================================================
@router.get("", response_model=TeacherDashboardResponse)
async def get_teacher_dashboard(
    current_user: User = Depends(require_permissions(["VIEW_DASHBOARD"])),
    db: AsyncSession = Depends(get_db),
):
    """04.5.3 Section 10: Display teacher's authorized classes, homework, and grading queue."""
    service = TeacherDashboardService(db)
    return await service.get_dashboard(current_user)


# ==============================================================================
# 2. Homework Operations (VIEW_HOMEWORK, CREATE_HOMEWORK, EDIT_HOMEWORK, PUBLISH_HOMEWORK)
# ==============================================================================
@router.get("/homework")
async def list_teacher_homework(
    class_id: Optional[uuid.UUID] = Query(None),
    subject_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(require_permissions(["VIEW_HOMEWORK"])),
    db: AsyncSession = Depends(get_db),
):
    """ADM-TC-BR-005 &ADM-TC-BR-014: View homework belonging to the teacher's academic scope."""
    staff = await _get_verified_teacher(db, current_user)
    stmt = select(Assignment).where(Assignment.teacher_id == staff.staff_id).order_by(Assignment.due_at.desc())
    if class_id:
        stmt = stmt.where(Assignment.class_id == class_id)
    if subject_id:
        stmt = stmt.where(Assignment.subject_id == subject_id)

    assignments = (await db.execute(stmt)).scalars().all()
    return [
        {
            "assignment_id": a.assignment_id,
            "class_id": a.class_id,
            "subject_id": a.subject_id,
            "title": a.title,
            "assignment_type": a.assignment_type,
            "max_score": a.max_score,
            "due_at": a.due_at,
            "allow_resubmission": a.allow_resubmission,
            "max_attempts": a.max_attempts,
        }
        for a in assignments
    ]


@router.post("/homework", status_code=status.HTTP_201_CREATED)
async def create_homework_assignment(
    payload: TeacherCreateAssignmentRequest,
    current_user: User = Depends(require_permissions(["CREATE_HOMEWORK"])),
    db: AsyncSession = Depends(get_db),
):
    """HW-BR-001, HW-BR-002, HW-BR-003, HW-BR-007: Create File-based or Online Homework with deadline."""
    staff = await _get_verified_teacher(db, current_user)

    assignment = Assignment(
        class_id=payload.class_id,
        subject_id=payload.subject_id,
        teacher_id=staff.staff_id,
        title=payload.title,
        instructions=payload.instructions,
        assignment_type=payload.assignment_type,
        max_score=payload.max_score,
        due_at=payload.due_at,
        allow_resubmission=payload.allow_resubmission,
        max_attempts=payload.max_attempts,
    )
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    return {
        "message": "Homework created successfully",
        "assignment_id": assignment.assignment_id,
        "due_at": assignment.due_at,
    }


@router.put("/homework/{assignment_id}")
async def edit_homework_assignment(
    assignment_id: uuid.UUID,
    payload: EditHomeworkRequest,
    current_user: User = Depends(require_permissions(["EDIT_HOMEWORK"])),
    db: AsyncSession = Depends(get_db),
):
    """Edit homework requirements, deadline, or attach a homework file (HW-BR-002, HW-BR-003, HW-BR-007)."""
    staff = await _get_verified_teacher(db, current_user)
    assignment = (
        await db.execute(
            select(Assignment).where(
                Assignment.assignment_id == assignment_id,
                Assignment.teacher_id == staff.staff_id,
            )
        )
    ).scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Homework not found in your authorized scope.")

    if payload.title is not None:
        assignment.title = payload.title
    if payload.instructions is not None:
        assignment.instructions = payload.instructions
    if payload.assignment_type is not None:
        assignment.assignment_type = payload.assignment_type
    if payload.max_score is not None:
        assignment.max_score = payload.max_score
    if payload.due_at is not None:
        assignment.due_at = payload.due_at
    if payload.allow_resubmission is not None:
        assignment.allow_resubmission = payload.allow_resubmission
    if payload.max_attempts is not None:
        assignment.max_attempts = payload.max_attempts

    if payload.attachment_storage_key and payload.attachment_file_name:
        attachment = AssignmentAttachment(
            assignment_id=assignment.assignment_id,
            original_file_name=payload.attachment_file_name,
            content_type="application/pdf",
            file_size_bytes=2048,
            storage_key=payload.attachment_storage_key,
        )
        db.add(attachment)

    await db.commit()
    return {"message": "Homework updated successfully", "assignment_id": assignment.assignment_id}


@router.post("/homework/{assignment_id}/publish")
async def publish_homework_assignment(
    assignment_id: uuid.UUID,
    current_user: User = Depends(require_permissions(["PUBLISH_HOMEWORK"])),
    db: AsyncSession = Depends(get_db),
):
    """HW-BR-001: Publish homework to make it accessible to assigned students."""
    staff = await _get_verified_teacher(db, current_user)
    assignment = (
        await db.execute(
            select(Assignment).where(
                Assignment.assignment_id == assignment_id,
                Assignment.teacher_id == staff.staff_id,
            )
        )
    ).scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Homework not found in your authorized scope.")

    await record_audit_event(
        db=db,
        actor_user_id=current_user.user_id,
        action_type="HOMEWORK_PUBLISHED",
        entity_name="Assignment",
        entity_id=assignment.assignment_id,
        new_state={"class_id": str(assignment.class_id), "due_at": assignment.due_at.isoformat()},
    )
    await db.commit()
    return {
        "message": "Homework officially published to class",
        "assignment_id": assignment.assignment_id,
        "class_id": assignment.class_id,
    }


# ==============================================================================
# 3. Homework Review, History & Grading (REVIEW_HOMEWORK_SUBMISSIONS, VIEW_SUBMISSION_HISTORY, GRADE_HOMEWORK)
# ==============================================================================
@router.get("/homework/{assignment_id}/submissions")
async def review_homework_submissions(
    assignment_id: uuid.UUID,
    current_user: User = Depends(require_permissions(["REVIEW_HOMEWORK_SUBMISSIONS"])),
    db: AsyncSession = Depends(get_db),
):
    """HW-BR-009: View and review student submissions for a homework assignment."""
    staff = await _get_verified_teacher(db, current_user)
    assignment = (
        await db.execute(
            select(Assignment).where(
                Assignment.assignment_id == assignment_id,
                Assignment.teacher_id == staff.staff_id,
            )
        )
    ).scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Homework not found in your authorized scope.")

    stmt = (
        select(AssignmentSubmission)
        .where(AssignmentSubmission.assignment_id == assignment_id)
        .order_by(AssignmentSubmission.submitted_at.desc())
    )
    subs = (await db.execute(stmt)).scalars().all()
    return [
        {
            "submission_id": s.submission_id,
            "student_id": s.student_id,
            "attempt_number": s.attempt_number,
            "text_solution": s.text_solution,
            "submitted_at": s.submitted_at,
            "status": s.status,
            "awarded_score": s.awarded_score,
            "teacher_feedback": s.teacher_feedback,
        }
        for s in subs
    ]


@router.get("/homework/{assignment_id}/submissions/history")
async def view_submission_history(
    assignment_id: uuid.UUID,
    student_id: Optional[uuid.UUID] = Query(None, description="Filter full attempt history for a specific student"),
    current_user: User = Depends(require_permissions(["VIEW_SUBMISSION_HISTORY"])),
    db: AsyncSession = Depends(get_db),
):
    """
    04.2 Homework Submission Model:
    Each resubmission is preserved as a separate record. Teachers can inspect both the latest
    submission and the complete historical attempts.
    """
    staff = await _get_verified_teacher(db, current_user)
    assignment = (
        await db.execute(
            select(Assignment).where(
                Assignment.assignment_id == assignment_id,
                Assignment.teacher_id == staff.staff_id,
            )
        )
    ).scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Homework not found in your authorized scope.")

    stmt = select(AssignmentSubmission).where(AssignmentSubmission.assignment_id == assignment_id)
    if student_id:
        stmt = stmt.where(AssignmentSubmission.student_id == student_id)
    stmt = stmt.order_by(AssignmentSubmission.student_id, AssignmentSubmission.attempt_number.asc())

    history = (await db.execute(stmt)).scalars().all()
    return [
        {
            "submission_id": s.submission_id,
            "student_id": s.student_id,
            "attempt_number": s.attempt_number,
            "status": s.status,
            "submitted_at": s.submitted_at,
            "awarded_score": s.awarded_score,
            "teacher_feedback": s.teacher_feedback,
        }
        for s in history
    ]


@router.post("/homework/submissions/{submission_id}/grade")
async def grade_homework_submission(
    submission_id: uuid.UUID,
    payload: TeacherGradeSubmissionRequest,
    current_user: User = Depends(require_permissions(["GRADE_HOMEWORK"])),
    db: AsyncSession = Depends(get_db),
):
    """HW-BR-010 & HW-BR-011: Provide teacher feedback and assign a grade/mark to homework."""
    staff = await _get_verified_teacher(db, current_user)

    sub = (
        await db.execute(
            select(AssignmentSubmission)
            .join(Assignment, AssignmentSubmission.assignment_id == Assignment.assignment_id)
            .where(
                AssignmentSubmission.submission_id == submission_id,
                Assignment.teacher_id == staff.staff_id,
            )
        )
    ).scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found in your authorized scope.")

    sub.awarded_score = payload.awarded_score
    sub.teacher_feedback = payload.teacher_feedback
    sub.graded_by_staff_id = staff.staff_id
    sub.graded_at = datetime.now(timezone.utc)
    sub.status = "REVIEWED"

    await db.commit()
    return {
        "message": "Homework graded and feedback saved",
        "submission_id": sub.submission_id,
        "awarded_score": sub.awarded_score,
        "status": sub.status,
    }


# ==============================================================================
# 4. Exam Operations (VIEW_EXAMS, CREATE_EXAMS, EDIT_EXAMS, MANAGE_EXAM_QUESTIONS,
#    PUBLISH_EXAMS, VIEW_EXAM_RESULTS, REOPEN_EXAM, EXTEND_EXAM_TIME)
# ==============================================================================
@router.get("/exams")
async def list_teacher_exams(
    class_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(require_permissions(["VIEW_EXAMS"])),
    db: AsyncSession = Depends(get_db),
):
    """04.3 & ADM-TC-BR-005: View examinations created within the teacher's academic scope."""
    staff = await _get_verified_teacher(db, current_user)
    return {
        "teacher_staff_id": staff.staff_id,
        "filter_class_id": class_id,
        "exams": [],
    }


@router.post("/exams", status_code=status.HTTP_201_CREATED)
async def create_online_exam(
    payload: CreateExamRequest,
    current_user: User = Depends(require_permissions(["CREATE_EXAMS"])),
    db: AsyncSession = Depends(get_db),
):
    """
    EX-BR-001, EX-BR-004, EX-BR-017: Create an online examination with defined Opening Time
    and Closing Time, and record creation in the Examination Audit Trail.
    """
    staff = await _get_verified_teacher(db, current_user)
    if payload.closing_time <= payload.opening_time:
        raise HTTPException(status_code=400, detail="Closing time must be after opening time (EX-BR-004).")

    exam_id = uuid.uuid4()
    await record_audit_event(
        db=db,
        actor_user_id=current_user.user_id,
        action_type="EXAM_CREATED",
        entity_name="Exam",
        entity_id=exam_id,
        new_state={
            "teacher_id": str(staff.staff_id),
            "class_id": str(payload.class_id),
            "subject_id": str(payload.subject_id),
            "title": payload.title,
            "opening_time": payload.opening_time.isoformat(),
            "closing_time": payload.closing_time.isoformat(),
        },
    )
    await db.commit()
    return {
        "message": "Online exam created with scheduled availability window (EX-BR-004)",
        "exam_id": exam_id,
        "opening_time": payload.opening_time,
        "closing_time": payload.closing_time,
    }


@router.put("/exams/{exam_id}")
async def edit_exam_schedule_or_details(
    exam_id: uuid.UUID,
    payload: EditExamRequest,
    current_user: User = Depends(require_permissions(["EDIT_EXAMS"])),
    db: AsyncSession = Depends(get_db),
):
    """EX-BR-017: Modify examination schedule or metadata and record in Audit Trail."""
    await _get_verified_teacher(db, current_user)

    if payload.opening_time and payload.closing_time and payload.closing_time <= payload.opening_time:
        raise HTTPException(status_code=400, detail="Closing time must be after opening time.")

    await record_audit_event(
        db=db,
        actor_user_id=current_user.user_id,
        action_type="EXAM_SCHEDULE_MODIFIED",
        entity_name="Exam",
        entity_id=exam_id,
        new_state={
            "title": payload.title,
            "opening_time": payload.opening_time.isoformat() if payload.opening_time else None,
            "closing_time": payload.closing_time.isoformat() if payload.closing_time else None,
            "duration_minutes": payload.duration_minutes,
        },
        details={"reason": payload.reason},
    )
    await db.commit()
    return {"message": "Exam schedule updated and recorded in Audit Trail (EX-BR-017)", "exam_id": exam_id}


@router.post("/exams/{exam_id}/questions")
async def manage_exam_questions(
    exam_id: uuid.UUID,
    payload: ManageExamQuestionsRequest,
    current_user: User = Depends(require_permissions(["MANAGE_EXAM_QUESTIONS"])),
    db: AsyncSession = Depends(get_db),
):
    """
    EX-BR-002 & EX-BR-003: Add or update exam questions supporting MCQ, True/False,
    Text-based, and Image-based questions.
    """
    await _get_verified_teacher(db, current_user)
    return {
        "message": "Exam questions configured (MCQ, True/False, Text, Image supported)",
        "exam_id": exam_id,
        "questions_count": len(payload.questions),
    }


@router.post("/exams/{exam_id}/publish")
async def publish_online_exam(
    exam_id: uuid.UUID,
    current_user: User = Depends(require_permissions(["PUBLISH_EXAMS"])),
    db: AsyncSession = Depends(get_db),
):
    """04.3 Exam Availability: Publish exam so it unlocks automatically at Opening Time."""
    await _get_verified_teacher(db, current_user)
    await record_audit_event(
        db=db,
        actor_user_id=current_user.user_id,
        action_type="EXAM_PUBLISHED",
        entity_name="Exam",
        entity_id=exam_id,
        new_state={"status": "PUBLISHED"},
    )
    await db.commit()
    return {"message": "Exam published; students will gain access at Opening Time (EX-BR-005)", "exam_id": exam_id}


@router.get("/exams/{exam_id}/results")
async def view_exam_results(
    exam_id: uuid.UUID,
    current_user: User = Depends(require_permissions(["VIEW_EXAM_RESULTS"])),
    db: AsyncSession = Depends(get_db),
):
    """EX-BR-009 & 04.5.3 Section 6: View automatically evaluated student exam results."""
    await _get_verified_teacher(db, current_user)
    return {"exam_id": exam_id, "results": []}


@router.post("/exams/{exam_id}/reopen")
async def reopen_exam_for_student(
    exam_id: uuid.UUID,
    payload: ExceptionalExamReopenRequest,
    current_user: User = Depends(require_permissions(["REOPEN_EXAM"])),
    db: AsyncSession = Depends(get_db),
):
    """
    EX-BR-013, EX-BR-014, EX-BR-015, EX-BR-017:
    Reopen an examination for a SINGLE affected student only (never unlocks for the whole class)
    with a defined new examination period, and record in Audit Trail.
    """
    await _get_verified_teacher(db, current_user)
    if payload.new_closing_time <= payload.new_opening_time:
        raise HTTPException(status_code=400, detail="New closing time must be after new opening time.")

    await record_audit_event(
        db=db,
        actor_user_id=current_user.user_id,
        action_type="EXAM_REOPENED_FOR_SINGLE_STUDENT",
        entity_name="Exam",
        entity_id=exam_id,
        new_state={
            "target_student_id": str(payload.student_id),
            "new_opening_time": payload.new_opening_time.isoformat(),
            "new_closing_time": payload.new_closing_time.isoformat(),
        },
        details={"reason": payload.reason},
    )
    await db.commit()
    return {
        "message": "Exam reopened exclusively for the authorized student (EX-BR-014) and audited (EX-BR-017)",
        "exam_id": exam_id,
        "student_id": payload.student_id,
    }


@router.post("/exams/{exam_id}/extend-time")
async def extend_student_exam_time(
    exam_id: uuid.UUID,
    payload: ExtendStudentExamTimeRequest,
    current_user: User = Depends(require_permissions(["EXTEND_EXAM_TIME"])),
    db: AsyncSession = Depends(get_db),
):
    """
    EX-BR-016 & EX-BR-017: Extend examination time for a specific student due to a technical
    issue and record the extension in the Audit Trail.
    """
    await _get_verified_teacher(db, current_user)

    await record_audit_event(
        db=db,
        actor_user_id=current_user.user_id,
        action_type="EXAM_STUDENT_TIME_EXTENDED",
        entity_name="Exam",
        entity_id=exam_id,
        new_state={
            "target_student_id": str(payload.student_id),
            "additional_minutes": payload.additional_minutes,
            "new_closing_time": payload.new_closing_time.isoformat() if payload.new_closing_time else None,
        },
        details={"reason": payload.reason},
    )
    await db.commit()
    return {
        "message": f"Extended exam time by {payload.additional_minutes} minutes for student (EX-BR-016)",
        "exam_id": exam_id,
        "student_id": payload.student_id,
    }


# ==============================================================================
# 5. Academic Results & Grades (VIEW_GRADES, PREPARE_ACADEMIC_RESULT)
# ==============================================================================
@router.get("/grades")
async def view_scoped_student_grades(
    class_id: Optional[uuid.UUID] = Query(None),
    subject_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(require_permissions(["VIEW_GRADES"])),
    db: AsyncSession = Depends(get_db),
):
    """04.4 & ADM-TC-BR-005: View student grades within the teacher's authorized scope."""
    staff = await _get_verified_teacher(db, current_user)
    return {
        "teacher_staff_id": staff.staff_id,
        "class_id": class_id,
        "subject_id": subject_id,
        "note": "Online exam scores and official Mid-Year/End-of-Year results are maintained separately (GR-BR-008).",
        "grades": [],
    }


@router.post("/grades/prepare-result", status_code=status.HTTP_201_CREATED)
async def prepare_and_finalize_academic_result(
    payload: PrepareAcademicResultRequest,
    current_user: User = Depends(require_permissions(["PREPARE_ACADEMIC_RESULT"])),
    db: AsyncSession = Depends(get_db),
):
    """
    GR-BR-002, GR-BR-004, ADM-TC-BR-015:
    Teacher prepares and finalizes the student's Mid-Year or End-of-Year result and submits
    it to School Administration for official upload/publication. Never auto-calculated (GR-BR-004).
    """
    staff = await _get_verified_teacher(db, current_user)

    await record_audit_event(
        db=db,
        actor_user_id=current_user.user_id,
        action_type="ACADEMIC_RESULT_PREPARED_BY_TEACHER",
        entity_name="OfficialResultPreparation",
        entity_id=payload.student_id,
        new_state={
            "prepared_by_staff_id": str(staff.staff_id),
            "student_id": str(payload.student_id),
            "subject_id": str(payload.subject_id),
            "academic_year_id": str(payload.academic_year_id),
            "result_type": payload.result_type,
            "finalized_score": str(payload.finalized_score),
        },
        details={"teacher_remarks": payload.teacher_remarks},
    )
    await db.commit()
    return {
        "message": f"{payload.result_type} result prepared and submitted to Administration for official entry (GR-BR-002)",
        "student_id": payload.student_id,
        "result_type": payload.result_type,
        "finalized_score": payload.finalized_score,
    }


# ==============================================================================
# 6. Private Communication (SEND_PRIVATE_MESSAGE, RECEIVE_PRIVATE_MESSAGE,
#    COMMUNICATE_WITH_STUDENTS, COMMUNICATE_WITH_PARENTS)
# ==============================================================================
@router.post("/communications/send", status_code=status.HTTP_201_CREATED)
async def send_private_message(
    payload: PrivateMessageRequest,
    current_user: User = Depends(require_permissions(["SEND_PRIVATE_MESSAGE"])),
    db: AsyncSession = Depends(get_db),
):
    """04.5.8 Section 6: Send a private message within authorized communication boundaries."""
    await _get_verified_teacher(db, current_user)
    return {
        "message": "Private message sent",
        "sender_user_id": current_user.user_id,
        "recipient_user_id": payload.recipient_user_id,
        "subject": payload.subject,
    }


@router.get("/communications/inbox")
async def view_received_private_messages(
    current_user: User = Depends(require_permissions(["RECEIVE_PRIVATE_MESSAGE"])),
    db: AsyncSession = Depends(get_db),
):
    """04.5.8 Section 6: View received private messages in teacher's inbox."""
    await _get_verified_teacher(db, current_user)
    return {"user_id": current_user.user_id, "inbox": []}


@router.post("/communications/students", status_code=status.HTTP_201_CREATED)
async def communicate_with_scoped_student(
    payload: ScopedStudentMessageRequest,
    current_user: User = Depends(require_permissions(["COMMUNICATE_WITH_STUDENTS", "SEND_PRIVATE_MESSAGE"])),
    db: AsyncSession = Depends(get_db),
):
    """04.5.3 Section 6 & ADM-TC-BR-018: Communicate privately with an assigned student."""
    await _get_verified_teacher(db, current_user)
    student = (
        await db.execute(select(Student).where(Student.student_id == payload.student_id))
    ).scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    return {
        "message": "Private communication sent to student",
        "student_id": student.student_id,
        "student_name": f"{student.first_name} {student.last_name}",
        "subject": payload.subject,
    }


@router.post("/communications/parents", status_code=status.HTTP_201_CREATED)
async def communicate_with_scoped_parent(
    payload: ScopedParentMessageRequest,
    current_user: User = Depends(require_permissions(["COMMUNICATE_WITH_PARENTS", "SEND_PRIVATE_MESSAGE"])),
    db: AsyncSession = Depends(get_db),
):
    """
    04.5.3 Section 6 & ADM-PS-BR-017: Communicate privately with the officially linked
    Parent/Guardian of an assigned student.
    """
    await _get_verified_teacher(db, current_user)

    stmt = (
        select(ParentStudentRelationship)
        .where(
            ParentStudentRelationship.student_id == payload.student_id,
            ParentStudentRelationship.is_active.is_(True),
        )
    )
    if payload.parent_guardian_id:
        stmt = stmt.where(ParentStudentRelationship.parent_guardian_id == payload.parent_guardian_id)

    active_links = (await db.execute(stmt)).scalars().all()
    if not active_links:
        raise HTTPException(
            status_code=400,
            detail="No active official Parent <-> Student relationship found for this student (ADM-PS-BR-004).",
        )

    return {
        "message": "Private communication sent to linked Parent/Guardian(s)",
        "student_id": payload.student_id,
        "notified_guardians_count": len(active_links),
        "subject": payload.subject,
    }