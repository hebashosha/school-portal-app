import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, TYPE_CHECKING
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.academic import ClassModel, Subject
    from app.models.stakeholder import Student, StaffMember

class Exam(Base):
    __tablename__ = "exams"

    exam_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("classes.class_id", ondelete="RESTRICT"), nullable=False
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.subject_id", ondelete="RESTRICT"), nullable=False
    )
    created_by_staff_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff_members.staff_id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    scheduled_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("duration_minutes > 0", name="chk_exam_duration"),
        CheckConstraint("max_attempts > 0", name="chk_exam_max_attempts"),
    )

    class_assigned: Mapped["ClassModel"] = relationship("ClassModel")
    questions: Mapped[List["ExamQuestion"]] = relationship("ExamQuestion", back_populates="exam", order_by="ExamQuestion.question_order")
    attempts: Mapped[List["ExamAttempt"]] = relationship("ExamAttempt", back_populates="exam")

class ExamQuestion(Base):
    __tablename__ = "exam_questions"

    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    exam_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exams.exam_id", ondelete="CASCADE"), nullable=False
    )
    question_order: Mapped[int] = mapped_column(Integer, nullable=False)
    question_type: Mapped[str] = mapped_column(String(20), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    image_storage_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    points: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("1.00"), nullable=False)

    __table_args__ = (
        CheckConstraint("question_order > 0", name="chk_question_order"),
        CheckConstraint("question_type IN ('MCQ', 'TRUE_FALSE', 'WRITTEN')", name="chk_question_type"),
        CheckConstraint("points > 0", name="chk_question_points"),
        UniqueConstraint("exam_id", "question_order", name="uq_exam_question_order"),
    )

    exam: Mapped["Exam"] = relationship("Exam", back_populates="questions")
    options: Mapped[List["ExamQuestionOption"]] = relationship("ExamQuestionOption", back_populates="question", order_by="ExamQuestionOption.option_order")

class ExamQuestionOption(Base):
    __tablename__ = "exam_question_options"

    option_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exam_questions.question_id", ondelete="CASCADE"), nullable=False
    )
    option_order: Mapped[int] = mapped_column(Integer, nullable=False)
    option_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        CheckConstraint("option_order > 0", name="chk_option_order"),
        UniqueConstraint("question_id", "option_order", name="uq_question_option_order"),
    )

    question: Mapped["ExamQuestion"] = relationship("ExamQuestion", back_populates="options")

class ExamAttempt(Base):
    __tablename__ = "exam_attempts"

    attempt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    exam_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exams.exam_id", ondelete="CASCADE"), nullable=False
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.student_id", ondelete="RESTRICT"), nullable=False
    )
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="IN_PROGRESS", nullable=False)

    __table_args__ = (
        CheckConstraint("attempt_number > 0", name="chk_attempt_number_positive"),
        CheckConstraint("status IN ('IN_PROGRESS', 'SUBMITTED', 'TIMED_OUT', 'REOPENED')", name="chk_attempt_status"),
        CheckConstraint("submitted_at IS NULL OR submitted_at >= started_at", name="chk_attempt_timestamps"),
        UniqueConstraint("exam_id", "student_id", "attempt_number", name="uq_exam_student_attempt"),
    )

    exam: Mapped["Exam"] = relationship("Exam", back_populates="attempts")
    student: Mapped["Student"] = relationship("Student")
    exceptions: Mapped[List["ExamAttemptException"]] = relationship("ExamAttemptException", back_populates="attempt")
    answers: Mapped[List["ExamAnswer"]] = relationship("ExamAnswer", back_populates="attempt")
    result: Mapped["ExamResult | None"] = relationship("ExamResult", back_populates="attempt", uselist=False)

class ExamAttemptException(Base):
    __tablename__ = "exam_attempt_exceptions"

    exception_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exam_attempts.attempt_id", ondelete="CASCADE"), nullable=False
    )
    approved_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False
    )
    exception_type: Mapped[str] = mapped_column(String(30), nullable=False)
    extended_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("exception_type IN ('REOPEN', 'TIME_EXTENSION')", name="chk_exam_exception_type"),
    )

    attempt: Mapped["ExamAttempt"] = relationship("ExamAttempt", back_populates="exceptions")

class ExamAnswer(Base):
    __tablename__ = "exam_answers"

    answer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exam_attempts.attempt_id", ondelete="CASCADE"), nullable=False
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exam_questions.question_id", ondelete="RESTRICT"), nullable=False
    )
    selected_option_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exam_question_options.option_id", ondelete="SET NULL"), nullable=True
    )
    written_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    awarded_points: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)

    __table_args__ = (
        CheckConstraint("awarded_points IS NULL OR awarded_points >= 0", name="chk_awarded_points_positive"),
        UniqueConstraint("attempt_id", "question_id", name="uq_attempt_question"),
    )

    attempt: Mapped["ExamAttempt"] = relationship("ExamAttempt", back_populates="answers")
    question: Mapped["ExamQuestion"] = relationship("ExamQuestion")
    selected_option: Mapped["ExamQuestionOption | None"] = relationship("ExamQuestionOption")

class ExamResult(Base):
    __tablename__ = "exam_results"

    result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exam_attempts.attempt_id", ondelete="CASCADE"), unique=True, nullable=False
    )
    total_points: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    earned_points: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("total_points >= 0", name="chk_total_points_positive"),
        CheckConstraint("earned_points >= 0", name="chk_earned_points_positive"),
        CheckConstraint("percentage >= 0 AND percentage <= 100", name="chk_percentage_bounds"),
        CheckConstraint("earned_points <= total_points", name="chk_earned_lte_total"),
    )

    attempt: Mapped["ExamAttempt"] = relationship("ExamAttempt", back_populates="result")