import uuid
from typing import Dict, List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.coursework import Assignment, AssignmentSubmission
from app.models.stakeholder import StaffMember


class TeacherDashboardRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_staff_by_user_id(self, user_id: uuid.UUID) -> Optional[StaffMember]:
        stmt = select(StaffMember).where(StaffMember.user_id == user_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_teacher_assignments(self, staff_id: uuid.UUID) -> List[Assignment]:
        stmt = (
            select(Assignment)
            .where(Assignment.teacher_id == staff_id)
            .order_by(Assignment.due_at.desc())
            .limit(10)
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_pending_grading_count(self, staff_id: uuid.UUID) -> int:
        stmt = (
            select(func.count(AssignmentSubmission.submission_id))
            .join(Assignment, AssignmentSubmission.assignment_id == Assignment.assignment_id)
            .where(
                Assignment.teacher_id == staff_id,
                AssignmentSubmission.status.in_(["SUBMITTED", "LATE"]),
                AssignmentSubmission.awarded_score.is_(None),
            )
        )
        return (await self.db.execute(stmt)).scalar() or 0

    async def get_assignment_metrics(self, assignment_id: uuid.UUID) -> Dict[str, int]:
        total_stmt = select(func.count(AssignmentSubmission.submission_id)).where(
            AssignmentSubmission.assignment_id == assignment_id
        )
        graded_stmt = select(func.count(AssignmentSubmission.submission_id)).where(
            AssignmentSubmission.assignment_id == assignment_id,
            AssignmentSubmission.awarded_score.is_not(None),
        )
        total = (await self.db.execute(total_stmt)).scalar() or 0
        graded = (await self.db.execute(graded_stmt)).scalar() or 0
        return {"submitted": total, "graded": graded}