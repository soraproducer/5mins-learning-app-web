from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException

from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/users")

@router.post("", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    service: UserService = Depends()
):
    """Create a new user"""
    return await service.create_user(user_data)

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    service: UserService = Depends()
):
    """Get a user by ID"""
    return await service.get_user(user_id)
