from datetime import date
from typing import Dict
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance import AttendanceChangeRequest, AttendanceOccurrence, AttendanceRecord


class DirectorDashboardRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_pending_attendance_change_requests_count(self) -> int:
        stmt = select(func.count(AttendanceChangeRequest.request_id)).where(
            AttendanceChangeRequest.request_status == "PENDING"
        )
        return (await self.db.execute(stmt)).scalar() or 0

    async def get_unauthorized_late_excused_count(self) -> Dict[str, int]:
        stmt = (
            select(AttendanceRecord.status, func.count(AttendanceRecord.attendance_record_id))
            .where(
                AttendanceRecord.status.in_(["LATE", "EXCUSED"]),
                AttendanceRecord.approved_by_user_id.is_(None),
            )
            .group_by(AttendanceRecord.status)
        )
        res = await self.db.execute(stmt)
        counts = {"LATE": 0, "EXCUSED": 0}
        for st, cnt in res.fetchall():
            counts[st.upper()] = cnt
        return counts

    async def get_today_attendance_summary(self) -> Dict[str, int]:
        today = date.today()
        stmt = (
            select(AttendanceRecord.status, func.count(AttendanceRecord.attendance_record_id))
            .join(AttendanceOccurrence, AttendanceRecord.occurrence_id == AttendanceOccurrence.occurrence_id)
            .where(AttendanceOccurrence.occurrence_date == today)
            .group_by(AttendanceRecord.status)
        )
        res = await self.db.execute(stmt)
        summary = {"PRESENT": 0, "ABSENT": 0, "LATE": 0, "EXCUSED": 0}
        for st, cnt in res.fetchall():
            if st.upper() in summary:
                summary[st.upper()] = cnt
        return summary