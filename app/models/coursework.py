import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, TYPE_CHECKING
from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.academic import ClassModel, Subject
    from app.models.stakeholder import StaffMember, Student

class Assignment(Base, TimestampMixin):
    __tablename__ = "assignments"

    assignment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("classes.class_id", ondelete="RESTRICT"), nullable=False
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.subject_id", ondelete="RESTRICT"), nullable=False
    )
    teacher_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff_members.staff_id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    assignment_type: Mapped[str] = mapped_column(String(30), default="HYBRID", nullable=False)
    max_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("100.00"), nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    allow_resubmission: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    __table_args__ = (
        CheckConstraint("assignment_type IN ('FILE_BASED', 'ONLINE_TEXT', 'HYBRID')", name="chk_assignment_type"),
        CheckConstraint("max_score > 0", name="chk_max_score_positive"),
        CheckConstraint("max_attempts > 0", name="chk_max_attempts_positive"),
    )

    class_assigned: Mapped["ClassModel"] = relationship("ClassModel")
    attachments: Mapped[List["AssignmentAttachment"]] = relationship("AssignmentAttachment", back_populates="assignment")
    submissions: Mapped[List["AssignmentSubmission"]] = relationship("AssignmentSubmission", back_populates="assignment")

class AssignmentAttachment(Base):
    __tablename__ = "assignment_attachments"

    attachment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    assignment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assignments.assignment_id", ondelete="CASCADE"), nullable=False
    )
    original_file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(150), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("file_size_bytes > 0", name="chk_assignment_file_size"),
    )

    assignment: Mapped["Assignment"] = relationship("Assignment", back_populates="attachments")

class AssignmentSubmission(Base):
    __tablename__ = "assignment_submissions"

    submission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    assignment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assignments.assignment_id", ondelete="CASCADE"), nullable=False
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.student_id", ondelete="RESTRICT"), nullable=False
    )
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    text_solution: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="SUBMITTED", nullable=False)
    awarded_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    teacher_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    graded_by_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff_members.staff_id", ondelete="SET NULL"), nullable=True
    )
    graded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("attempt_number > 0", name="chk_submission_attempt"),
        CheckConstraint("status IN ('DRAFT', 'SUBMITTED', 'LATE', 'REVIEWED')", name="chk_submission_status"),
        CheckConstraint("awarded_score IS NULL OR (awarded_score >= 0 AND awarded_score <= 1000)", name="chk_awarded_score"),
        UniqueConstraint("assignment_id", "student_id", "attempt_number", name="uq_assignment_attempt"),
    )

    assignment: Mapped["Assignment"] = relationship("Assignment", back_populates="submissions")
    student: Mapped["Student"] = relationship("Student")
    attachments: Mapped[List["SubmissionAttachment"]] = relationship("SubmissionAttachment", back_populates="submission")

class SubmissionAttachment(Base):
    __tablename__ = "submission_attachments"

    submission_attachment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    submission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assignment_submissions.submission_id", ondelete="CASCADE"), nullable=False
    )
    original_file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(150), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("file_size_bytes > 0", name="chk_sub_attachment_size"),
    )

    submission: Mapped["AssignmentSubmission"] = relationship("AssignmentSubmission", back_populates="attachments")