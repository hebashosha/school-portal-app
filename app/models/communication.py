import uuid
from datetime import datetime
from typing import List, TYPE_CHECKING
from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.stakeholder import Student
    from app.models.user import User

class Conversation(Base):
    __tablename__ = "conversations"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.student_id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE', 'CLOSED')", name="chk_conversation_status"),
        CheckConstraint(
            "(status = 'ACTIVE' AND closed_at IS NULL) OR (status = 'CLOSED' AND closed_at IS NOT NULL)",
            name="chk_conversation_closed_state",
        ),
    )

    student: Mapped["Student"] = relationship("Student")
    participants: Mapped[List["ConversationParticipant"]] = relationship("ConversationParticipant", back_populates="conversation")
    messages: Mapped[List["Message"]] = relationship("Message", back_populates="conversation", order_by="Message.created_at")
    meetings: Mapped[List["Meeting"]] = relationship("Meeting", back_populates="conversation")

class ConversationParticipant(Base):
    __tablename__ = "conversation_participants"

    participant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.conversation_id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False
    )
    participant_type: Mapped[str] = mapped_column(String(20), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("participant_type IN ('PARENT', 'STAFF')", name="chk_participant_type"),
        CheckConstraint("left_at IS NULL OR left_at >= joined_at", name="chk_participant_dates"),
        UniqueConstraint("conversation_id", "user_id", name="uq_conversation_user"),
    )

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="participants")
    user: Mapped["User"] = relationship("User")

class Message(Base):
    __tablename__ = "messages"

    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.conversation_id", ondelete="CASCADE"), nullable=False
    )
    sender_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False
    )
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("length(btrim(message_text)) > 0", name="chk_message_text_not_empty"),
    )

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")
    sender: Mapped["User"] = relationship("User")
    attachments: Mapped[List["MessageAttachment"]] = relationship("MessageAttachment", back_populates="message")

class MessageAttachment(Base):
    __tablename__ = "message_attachments"

    attachment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.message_id", ondelete="CASCADE"), nullable=False
    )
    original_file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(150), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("file_size_bytes > 0", name="chk_msg_attachment_size"),
    )

    message: Mapped["Message"] = relationship("Message", back_populates="attachments")

class Meeting(Base, TimestampMixin):
    __tablename__ = "meetings"

    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.conversation_id", ondelete="CASCADE"), nullable=False
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.student_id", ondelete="CASCADE"), nullable=False
    )
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False
    )
    platform: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="REQUESTED", nullable=False)
    scheduled_start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scheduled_end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    meeting_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint("platform IN ('ZOOM', 'MICROSOFT_TEAMS', 'GOOGLE_MEET', 'IN_PERSON')", name="chk_meeting_platform"),
        CheckConstraint(
            "status IN ('REQUESTED', 'ACCEPTED', 'REJECTED', 'RESCHEDULE_REQUESTED', 'CANCELLED', 'COMPLETED')",
            name="chk_meeting_status",
        ),
        CheckConstraint("scheduled_end_at > scheduled_start_at", name="chk_meeting_duration"),
    )

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="meetings")
    student: Mapped["Student"] = relationship("Student")
    requester: Mapped["User"] = relationship("User")