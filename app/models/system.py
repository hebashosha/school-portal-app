import uuid
from datetime import datetime
from typing import Any, Dict
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class SchoolSetting(Base):
    __tablename__ = "school_settings"

    setting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    setting_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    setting_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), default="GENERAL", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

class AuditLog(Base):
    __tablename__ = "audit_logs"

    audit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_name: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    previous_state: Mapped[Dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    new_state: Mapped[Dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    operation_result: Mapped[str] = mapped_column(String(20), default="SUCCESS", nullable=False)
    details: Mapped[Dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    client_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    event_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    __table_args__ = (
        CheckConstraint("operation_result IN ('SUCCESS', 'DENIED', 'FAILED')", name="chk_audit_operation_result"),
    )