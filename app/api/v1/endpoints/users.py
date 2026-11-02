# app/api/v1/endpoints/users.py
from typing import List
from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_user_repository, get_user_service
from app.repositories.user_repo import UserRepository
from app.schemas.user import UserCreate, UserResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    user_service: UserService = Depends(get_user_service),
):
    return await user_service.register_user(payload)


@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user_repo: UserRepository = Depends(get_user_repository),
):
    return await user_repo.get_all(skip=skip, limit=limit)