from uuid import UUID
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db_session
from app.models.user import User
from app.schemas.user import UserCreate, UserDB


class UserService:
    """Service for handling user operations"""

    def __init__(self, db: AsyncSession = Depends(get_db_session)):
        self.db = db

    async def create_user(self, user_data: UserCreate) -> UserDB:
        """Create a new user"""
        user = User(user_name=user_data.user_name)
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def get_user(self, user_id: UUID) -> UserDB:
        """Get a user by ID"""
        result = await self.db.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalars().first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return user

    async def update_user(self, user_id: UUID, user_data: dict) -> UserDB:
        """Update a user by ID"""
        result = await self.db.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalars().first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        for key, value in user_data.items():
            if value is not None:
                setattr(user, key, value)
        
        await self.db.commit()
        await self.db.refresh(user)
        
        return user

    async def delete_user(self, user_id: UUID) -> bool:
        """Delete a user by ID"""
        result = await self.db.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalars().first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        await self.db.delete(user)
        await self.db.commit()
        
        return True

    async def get_or_create_user(self, user_name: str = None) -> UserDB:
        """
        Get a user by name or create a new one if not exists
        This simplifies the API for testing and demo purposes
        """
        if user_name:
            # Try to find user by name
            result = await self.db.execute(
                select(User).where(User.user_name == user_name)
            )
            user = result.scalars().first()
            
            if user:
                return user
        
        # Create a new user if not found or no name provided
        return await self.create_user(UserCreate(user_name=user_name))
