import uuid
from datetime import datetime
from typing import List, TYPE_CHECKING
from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.stakeholder import Student, StaffMember, ParentGuardian

class User(Base, TimestampMixin):
    __tablename__ = "users"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    roles: Mapped[List["Role"]] = relationship(
        "Role", secondary="user_roles", back_populates="users", lazy="selectin"
    )
    student_profile: Mapped["Student | None"] = relationship("Student", back_populates="user", uselist=False)
    staff_profile: Mapped["StaffMember | None"] = relationship("StaffMember", back_populates="user", uselist=False)
    parent_profile: Mapped["ParentGuardian | None"] = relationship("ParentGuardian", back_populates="user", uselist=False)

class Role(Base):
    __tablename__ = "roles"

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    role_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    role_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    is_system_role: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    users: Mapped[List["User"]] = relationship(
        "User", secondary="user_roles", back_populates="roles"
    )
    permissions: Mapped[List["Permission"]] = relationship(
        "Permission", secondary="role_permissions", back_populates="roles", lazy="selectin"
    )

class Permission(Base):
    __tablename__ = "permissions"

    permission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    permission_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    permission_name: Mapped[str] = mapped_column(String(150), nullable=False)
    module_category: Mapped[str] = mapped_column(String(50), nullable=False)

    roles: Mapped[List["Role"]] = relationship(
        "Role", secondary="role_permissions", back_populates="permissions"
    )

class UserRole(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.role_id", ondelete="RESTRICT"), primary_key=True
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.role_id", ondelete="CASCADE"), primary_key=True
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("permissions.permission_id", ondelete="CASCADE"), primary_key=True
    )