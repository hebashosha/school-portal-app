import uuid
from datetime import date
from typing import Dict
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance import AttendanceOccurrence, AttendanceRecord


class SupervisorDashboardRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_today_stats(self, supervisor_user_id: uuid.UUID) -> Dict[str, int]:
        today = date.today()
        recorded_classes = (
            await self.db.execute(
                select(func.count(distinct(AttendanceOccurrence.class_id))).where(
                    AttendanceOccurrence.recorded_by_user_id == supervisor_user_id,
                    AttendanceOccurrence.occurrence_date == today,
                )
            )
        ).scalar() or 0

        status_stmt = (
            select(AttendanceRecord.status, func.count(AttendanceRecord.attendance_record_id))
            .join(AttendanceOccurrence, AttendanceRecord.occurrence_id == AttendanceOccurrence.occurrence_id)
            .where(
                AttendanceOccurrence.recorded_by_user_id == supervisor_user_id,
                AttendanceOccurrence.occurrence_date == today,
            )
            .group_by(AttendanceRecord.status)
        )
        res = await self.db.execute(status_stmt)
        stats = {"PRESENT": 0, "ABSENT": 0, "LATE": 0, "EXCUSED": 0}
        for st, cnt in res.fetchall():
            if st.upper() in stats:
                stats[st.upper()] = cnt

        return {
            "recorded_classes": recorded_classes,
            "present": stats["PRESENT"],
            "absent": stats["ABSENT"],
            "late": stats["LATE"],
            "excused": stats["EXCUSED"],
            "pending_auth": stats["LATE"] + stats["EXCUSED"],
        }