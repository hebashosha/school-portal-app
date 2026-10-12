# app/api/v1/endpoints/users.py
import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from app.api.deps import get_user_service, get_user_repository
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])

# Spring Equivalent: @PostMapping + @ResponseStatus(HttpStatus.CREATED)
@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    user_service: UserService = Depends(get_user_service)
):
    return await user_service.register_user(payload)

# Spring Equivalent: @GetMapping
@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 50,
    user_repo: UserRepository = Depends(get_user_repository)
):
    return await user_repo.get_all(skip=skip, limit=limit)