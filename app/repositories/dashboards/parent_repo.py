import uuid
from datetime import date, datetime, timezone
from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance import AttendanceOccurrence, AttendanceRecord
from app.models.coursework import Assignment, AssignmentSubmission
from app.models.stakeholder import ParentGuardian, ParentStudentRelationship, Student


class ParentDashboardRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_linked_students(self, parent_user_id: uuid.UUID) -> List[Student]:
        stmt = (
            select(Student)
            .join(ParentStudentRelationship, Student.student_id == ParentStudentRelationship.student_id)
            .join(ParentGuardian, ParentStudentRelationship.parent_guardian_id == ParentGuardian.parent_guardian_id)
            .where(
                ParentGuardian.user_id == parent_user_id,
                ParentStudentRelationship.is_active.is_(True),
            )
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_child_today_attendance(self, student_id: uuid.UUID) -> Optional[str]:
        today = date.today()
        stmt = (
            select(AttendanceRecord.status)
            .join(AttendanceOccurrence, AttendanceRecord.occurrence_id == AttendanceOccurrence.occurrence_id)
            .where(
                AttendanceRecord.student_id == student_id,
                AttendanceOccurrence.occurrence_date == today,
            )
            .order_by(AttendanceOccurrence.created_at.desc())
            .limit(1)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_child_pending_homework_count(self, student_id: uuid.UUID) -> int:
        now = datetime.now(timezone.utc)
        subquery = (
            select(AssignmentSubmission.assignment_id)
            .where(AssignmentSubmission.student_id == student_id)
        )
        stmt = (
            select(func.count(Assignment.assignment_id))
            .where(
                Assignment.due_at >= now,
                Assignment.assignment_id.not_in(subquery),
            )
        )
        return (await self.db.execute(stmt)).scalar() or 0