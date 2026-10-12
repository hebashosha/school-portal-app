import uuid
from datetime import date, datetime
from typing import List, TYPE_CHECKING
from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.academic import ClassModel, Subject
    from app.models.stakeholder import Student
    from app.models.user import User

class AttendanceOccurrence(Base):
    __tablename__ = "attendance_occurrences"

    occurrence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("academic_years.academic_year_id", ondelete="RESTRICT"), nullable=False
    )
    class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("classes.class_id", ondelete="RESTRICT"), nullable=False
    )
    subject_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.subject_id", ondelete="SET NULL"), nullable=True
    )
    occurrence_date: Mapped[date] = mapped_column(Date, nullable=False)
    period_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recorded_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("class_id", "occurrence_date", "period_number", "subject_id", name="uq_attendance_occurrence"),
    )

    class_assigned: Mapped["ClassModel"] = relationship("ClassModel")
    records: Mapped[List["AttendanceRecord"]] = relationship("AttendanceRecord", back_populates="occurrence")

class AttendanceRecord(Base, TimestampMixin):
    __tablename__ = "attendance_records"

    attendance_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    occurrence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("attendance_occurrences.occurrence_id", ondelete="CASCADE"), nullable=False
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.student_id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('PRESENT', 'ABSENT', 'LATE', 'EXCUSED')", name="chk_attendance_status"),
        CheckConstraint("status IN ('PRESENT', 'ABSENT') OR approved_by_user_id IS NOT NULL", name="chk_approval_needed"),
        CheckConstraint("approved_by_user_id IS NULL OR approved_at IS NOT NULL", name="chk_approval_timestamp"),
        UniqueConstraint("occurrence_id", "student_id", name="uq_occurrence_student"),
    )

    occurrence: Mapped["AttendanceOccurrence"] = relationship("AttendanceOccurrence", back_populates="records")
    student: Mapped["Student"] = relationship("Student")
    change_requests: Mapped[List["AttendanceChangeRequest"]] = relationship("AttendanceChangeRequest", back_populates="record")

class AttendanceChangeRequest(Base):
    __tablename__ = "attendance_change_requests"

    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    attendance_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("attendance_records.attendance_record_id", ondelete="CASCADE"), nullable=False
    )
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False
    )
    old_status: Mapped[str] = mapped_column(String(20), nullable=False)
    new_status: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    request_status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False)
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("old_status IN ('PRESENT', 'ABSENT', 'LATE', 'EXCUSED')", name="chk_req_old_status"),
        CheckConstraint("new_status IN ('PRESENT', 'ABSENT', 'LATE', 'EXCUSED')", name="chk_req_new_status"),
        CheckConstraint("request_status IN ('PENDING', 'APPROVED', 'REJECTED')", name="chk_req_status"),
        CheckConstraint("old_status <> new_status", name="chk_status_differ"),
        CheckConstraint(
            "request_status = 'PENDING' OR (reviewed_by_user_id IS NOT NULL AND reviewed_at IS NOT NULL)",
            name="chk_review_complete",
        ),
    )

    record: Mapped["AttendanceRecord"] = relationship("AttendanceRecord", back_populates="change_requests")