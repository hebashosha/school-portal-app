import uuid
from datetime import date, datetime
from typing import List, TYPE_CHECKING
from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.stakeholder import Student, StaffMember

class AcademicYear(Base):
    __tablename__ = "academic_years"

    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        CheckConstraint("end_date > start_date", name="chk_academic_dates"),
    )

    classes: Mapped[List["ClassModel"]] = relationship("ClassModel", back_populates="academic_year")

class Grade(Base):
    __tablename__ = "grades"

    grade_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    classes: Mapped[List["ClassModel"]] = relationship("ClassModel", back_populates="grade")

class ClassModel(Base):
    __tablename__ = "classes"

    class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("academic_years.academic_year_id", ondelete="RESTRICT"), nullable=False
    )
    grade_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("grades.grade_id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        CheckConstraint("capacity IS NULL OR capacity > 0", name="chk_class_capacity"),
        UniqueConstraint("academic_year_id", "name", name="uq_class_year_name"),
    )

    academic_year: Mapped["AcademicYear"] = relationship("AcademicYear", back_populates="classes")
    grade: Mapped["Grade"] = relationship("Grade", back_populates="classes")
    enrollments: Mapped[List["StudentEnrollment"]] = relationship("StudentEnrollment", back_populates="class_assigned")
    allocations: Mapped[List["StaffAllocation"]] = relationship("StaffAllocation", back_populates="class_assigned")

class Subject(Base):
    __tablename__ = "subjects"

    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

class StudentEnrollment(Base):
    __tablename__ = "student_enrollments"

    enrollment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.student_id", ondelete="CASCADE"), nullable=False
    )
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("academic_years.academic_year_id", ondelete="RESTRICT"), nullable=False
    )
    class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("classes.class_id", ondelete="RESTRICT"), nullable=False
    )
    enrollment_status: Mapped[str] = mapped_column(String(30), default="ACTIVE", nullable=False)
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "enrollment_status IN ('ACTIVE', 'COMPLETED', 'TRANSFERRED', 'WITHDRAWN')",
            name="chk_enrollment_status",
        ),
        CheckConstraint("ended_at IS NULL OR ended_at >= enrolled_at", name="chk_enrollment_dates"),
        UniqueConstraint("student_id", "academic_year_id", name="uq_student_academic_year"),
    )

    student: Mapped["Student"] = relationship("Student", back_populates="enrollments")
    class_assigned: Mapped["ClassModel"] = relationship("ClassModel", back_populates="enrollments")

class StaffAllocation(Base):
    __tablename__ = "staff_allocations"

    allocation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    staff_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff_members.staff_id", ondelete="CASCADE"), nullable=False
    )
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("academic_years.academic_year_id", ondelete="RESTRICT"), nullable=False
    )
    class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("classes.class_id", ondelete="CASCADE"), nullable=False
    )
    subject_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.subject_id", ondelete="CASCADE"), nullable=True
    )
    allocation_role: Mapped[str] = mapped_column(String(30), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "allocation_role IN ('LEAD_TEACHER', 'CO_TEACHER', 'FLOOR_SUPERVISOR', 'SUBSTITUTE')",
            name="chk_allocation_role",
        ),
        UniqueConstraint("staff_id", "class_id", "subject_id", "allocation_role", name="uq_staff_allocation"),
    )

    staff: Mapped["StaffMember"] = relationship("StaffMember", back_populates="allocations")
    class_assigned: Mapped["ClassModel"] = relationship("ClassModel", back_populates="allocations")
    subject: Mapped["Subject | None"] = relationship("Subject")