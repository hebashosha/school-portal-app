# app/api/v1/router.py
from fastapi import APIRouter
from app.api.v1.endpoints import auth, users
from app.api.v1.endpoints.dashboards import dashboard_router
api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(dashboard_router)