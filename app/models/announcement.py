import uuid
from datetime import datetime
from typing import List, TYPE_CHECKING
from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.academic import Grade, ClassModel
    from app.models.user import User, Role

class Announcement(Base, TimestampMixin):
    __tablename__ = "announcements"

    announcement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    author_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default="NORMAL", nullable=False)
    target_scope: Mapped[str] = mapped_column(String(30), default="ALL", nullable=False)
    target_grade_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("grades.grade_id", ondelete="CASCADE"), nullable=True
    )
    target_class_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("classes.class_id", ondelete="CASCADE"), nullable=True
    )
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("priority IN ('LOW', 'NORMAL', 'HIGH', 'URGENT')", name="chk_announcement_priority"),
        CheckConstraint("target_scope IN ('ALL', 'GRADE', 'CLASS', 'ROLES_ONLY')", name="chk_announcement_target_scope"),
        CheckConstraint("expires_at IS NULL OR expires_at > published_at", name="chk_announcement_dates"),
        CheckConstraint(
            """(target_scope = 'ALL' AND target_grade_id IS NULL AND target_class_id IS NULL) OR
               (target_scope = 'GRADE' AND target_grade_id IS NOT NULL AND target_class_id IS NULL) OR
               (target_scope = 'CLASS' AND target_class_id IS NOT NULL) OR
               (target_scope = 'ROLES_ONLY')""",
            name="chk_announcement_scope_consistency",
        ),
    )

    author: Mapped["User"] = relationship("User")
    target_grade: Mapped["Grade | None"] = relationship("Grade")
    target_class: Mapped["ClassModel | None"] = relationship("ClassModel")

    role_targets: Mapped[List["AnnouncementRoleTarget"]] = relationship("AnnouncementRoleTarget", back_populates="announcement")
    attachments: Mapped[List["AnnouncementAttachment"]] = relationship("AnnouncementAttachment", back_populates="announcement")
    read_receipts: Mapped[List["AnnouncementRead"]] = relationship("AnnouncementRead", back_populates="announcement")

class AnnouncementRoleTarget(Base):
    __tablename__ = "announcement_role_targets"

    announcement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("announcements.announcement_id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.role_id", ondelete="CASCADE"), primary_key=True
    )

    announcement: Mapped["Announcement"] = relationship("Announcement", back_populates="role_targets")
    role: Mapped["Role"] = relationship("Role")

class AnnouncementAttachment(Base):
    __tablename__ = "announcement_attachments"

    attachment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    announcement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("announcements.announcement_id", ondelete="CASCADE"), nullable=False
    )
    original_file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(150), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("file_size_bytes > 0", name="chk_announcement_file_size"),
    )

    announcement: Mapped["Announcement"] = relationship("Announcement", back_populates="attachments")

class AnnouncementRead(Base):
    __tablename__ = "announcement_reads"

    announcement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("announcements.announcement_id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True
    )
    read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    announcement: Mapped["Announcement"] = relationship("Announcement", back_populates="read_receipts")
    user: Mapped["User"] = relationship("User")