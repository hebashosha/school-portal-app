import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.academic import Subject, AcademicYear
    from app.models.stakeholder import Student, StaffMember

class OfficialResultPeriod(Base):
    __tablename__ = "official_result_periods"

    period_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("academic_years.academic_year_id", ondelete="RESTRICT"), nullable=False
    )
    period_code: Mapped[str] = mapped_column(String(30), nullable=False)
    period_name: Mapped[str] = mapped_column(String(100), nullable=False)

    __table_args__ = (
        CheckConstraint("period_code IN ('MID_YEAR', 'END_OF_YEAR', 'TERM_1', 'TERM_2')", name="chk_result_period_code"),
        UniqueConstraint("academic_year_id", "period_code", name="uq_period_year_code"),
    )

class SubjectTermResult(Base):
    __tablename__ = "subject_term_results"

    subject_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.student_id", ondelete="RESTRICT"), nullable=False
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.subject_id", ondelete="RESTRICT"), nullable=False
    )
    period_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("official_result_periods.period_id", ondelete="RESTRICT"), nullable=False
    )
    numeric_mark: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    letter_grade: Mapped[str | None] = mapped_column(String(10), nullable=True)
    recorded_by_staff_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff_members.staff_id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("numeric_mark >= 0 AND numeric_mark <= 100", name="chk_numeric_mark_range"),
        UniqueConstraint("student_id", "subject_id", "period_id", name="uq_student_subject_term"),
    )

    student: Mapped["Student"] = relationship("Student")
    subject: Mapped["Subject"] = relationship("Subject")
    period: Mapped["OfficialResultPeriod"] = relationship("OfficialResultPeriod")

class OfficialReportCard(Base):
    __tablename__ = "official_report_cards"

    report_card_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.student_id", ondelete="RESTRICT"), nullable=False
    )
    period_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("official_result_periods.period_id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(30), default="DRAFT", nullable=False)
    finalized_by_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff_members.staff_id", ondelete="SET NULL"), nullable=True
    )
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    report_file_storage_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('DRAFT', 'FINALIZED', 'PUBLISHED')", name="chk_report_status"),
        CheckConstraint("status = 'DRAFT' OR finalized_by_staff_id IS NOT NULL", name="chk_report_finalized"),
        UniqueConstraint("student_id", "period_id", name="uq_student_report_period"),
    )

    student: Mapped["Student"] = relationship("Student")
    period: Mapped["OfficialResultPeriod"] = relationship("OfficialResultPeriod")
    finalized_by: Mapped["StaffMember | None"] = relationship("StaffMember")