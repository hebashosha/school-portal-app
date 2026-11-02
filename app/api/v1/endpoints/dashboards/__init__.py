# app/api/v1/endpoints/dashboards/__init__.py
from fastapi import APIRouter
from app.api.v1.endpoints.dashboards import (
    admin,
    assistant_teacher,
    director,
    parent,
    student,
    supervisor,
    teacher,
)

dashboard_router = APIRouter(prefix="/dashboard")
dashboard_router.include_router(admin.router)
dashboard_router.include_router(director.router)
dashboard_router.include_router(supervisor.router)
dashboard_router.include_router(teacher.router)
dashboard_router.include_router(assistant_teacher.router)
dashboard_router.include_router(student.router)
dashboard_router.include_router(parent.router)