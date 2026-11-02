# app/api/v1/endpoints/dashboard.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_permissions
from app.models.user import User
from app.schemas.dashboard import (
    AdminDashboardResponse,
    DirectorDashboardResponse,
    ParentDashboardResponse,
    SupervisorDashboardResponse,
    TeacherDashboardResponse,
)
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/admin", response_model=AdminDashboardResponse)
async def get_admin_dashboard(
    current_user: User = Depends(require_permissions(["VIEW_DASHBOARD", "VIEW_USERS"])),
    db: AsyncSession = Depends(get_db),
):
    service = DashboardService(db)
    return await service.get_admin_dashboard()


@router.get("/director", response_model=DirectorDashboardResponse)
async def get_director_dashboard(
    current_user: User = Depends(require_permissions(["VIEW_DASHBOARD", "MODIFY_ATTENDANCE"])),
    db: AsyncSession = Depends(get_db),
):
    service = DashboardService(db)
    return await service.get_director_dashboard()


@router.get("/supervisor", response_model=SupervisorDashboardResponse)
async def get_supervisor_dashboard(
    current_user: User = Depends(require_permissions(["VIEW_DASHBOARD", "RECORD_ATTENDANCE"])),
    db: AsyncSession = Depends(get_db),
):
    service = DashboardService(db)
    return await service.get_floor_supervisor_dashboard()


@router.get("/teacher", response_model=TeacherDashboardResponse)
async def get_teacher_dashboard(
    current_user: User = Depends(require_permissions(["VIEW_DASHBOARD", "CREATE_HOMEWORK"])),
    db: AsyncSession = Depends(get_db),
):
    service = DashboardService(db)
    return await service.get_teacher_dashboard(current_user)


@router.get("/parent", response_model=ParentDashboardResponse)
async def get_parent_dashboard(
    current_user: User = Depends(require_permissions(["VIEW_DASHBOARD"])),
    db: AsyncSession = Depends(get_db),
):
    service = DashboardService(db)
    return await service.get_parent_dashboard(current_user)