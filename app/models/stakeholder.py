import uuid
from datetime import date, datetime
from typing import List, TYPE_CHECKING
from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.academic import StudentEnrollment, StaffAllocation

class Student(Base, TimestampMixin):
    __tablename__ = "students"

    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="SET NULL"), unique=True, nullable=True
    )
    student_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    middle_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False)

    __table_args__ = (
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE', 'TRANSFERRED', 'GRADUATED', 'ARCHIVED')",
            name="chk_student_status",
        ),
    )

    user: Mapped["User | None"] = relationship("User", back_populates="student_profile")
    enrollments: Mapped[List["StudentEnrollment"]] = relationship("StudentEnrollment", back_populates="student")
    guardians: Mapped[List["ParentStudentRelationship"]] = relationship("ParentStudentRelationship", back_populates="student")

class StaffMember(Base, TimestampMixin):
    __tablename__ = "staff_members"

    staff_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="RESTRICT"), unique=True, nullable=False
    )
    employee_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    staff_type: Mapped[str] = mapped_column(String(30), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "staff_type IN ('TEACHER', 'ASSISTANT_TEACHER', 'FLOOR_SUPERVISOR', 'DIRECTOR', 'ADMIN_STAFF')",
            name="chk_staff_type",
        ),
    )

    user: Mapped["User"] = relationship("User", back_populates="staff_profile")
    allocations: Mapped[List["StaffAllocation"]] = relationship("StaffAllocation", back_populates="staff")

class ParentGuardian(Base):
    __tablename__ = "parent_guardians"

    parent_guardian_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="RESTRICT"), unique=True, nullable=False
    )
    parent_code: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="parent_profile")
    student_relationships: Mapped[List["ParentStudentRelationship"]] = relationship(
        "ParentStudentRelationship", back_populates="parent_guardian"
    )

class ParentStudentRelationship(Base):
    __tablename__ = "parent_student_relationships"

    relationship_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    parent_guardian_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parent_guardians.parent_guardian_id", ondelete="RESTRICT"), nullable=False
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.student_id", ondelete="RESTRICT"), nullable=False
    )
    relationship_type: Mapped[str] = mapped_column(String(50), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("parent_guardian_id", "student_id", name="uq_parent_student"),
    )

    parent_guardian: Mapped["ParentGuardian"] = relationship("ParentGuardian", back_populates="student_relationships")
    student: Mapped["Student"] = relationship("Student", back_populates="guardians")