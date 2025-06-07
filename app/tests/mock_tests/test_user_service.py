import uuid
import pytest
from fastapi import HTTPException

from app.schemas.user import UserCreate, UserUpdate


@pytest.mark.asyncio
async def test_create_user(user_service):
    """Test creating a new user"""
    # Setup
    user_data = UserCreate(user_name="Test User")
    
    # Execute
    user = await user_service.create_user(user_data)
    
    # Assert
    assert user is not None
    assert user.user_id is not None
    assert user.user_name == "Test User"
    assert user.created_at is not None
    assert user.updated_at is not None


@pytest.mark.asyncio
async def test_get_user(user_service, test_user):
    """Test getting a user by ID"""
    # Execute
    user = await user_service.get_user(test_user.user_id)
    
    # Assert
    assert user is not None
    assert user.user_id == test_user.user_id
    assert user.user_name == test_user.user_name


@pytest.mark.asyncio
async def test_get_user_not_found(user_service):
    """Test getting a non-existent user"""
    # Execute & Assert
    with pytest.raises(HTTPException) as excinfo:
        await user_service.get_user(uuid.uuid4())
    
    assert excinfo.value.status_code == 404
    assert "not found" in excinfo.value.detail


@pytest.mark.asyncio
async def test_update_user(user_service, test_user):
    """Test updating a user"""
    # Setup
    update_data = {"user_name": "Updated User Name"}
    
    # Execute
    updated_user = await user_service.update_user(test_user.user_id, update_data)
    
    # Assert
    assert updated_user is not None
    assert updated_user.user_id == test_user.user_id
    assert updated_user.user_name == "Updated User Name"


@pytest.mark.asyncio
async def test_update_user_not_found(user_service):
    """Test updating a non-existent user"""
    # Setup
    update_data = {"user_name": "Updated User Name"}
    
    # Execute & Assert
    with pytest.raises(HTTPException) as excinfo:
        await user_service.update_user(uuid.uuid4(), update_data)
    
    assert excinfo.value.status_code == 404
    assert "not found" in excinfo.value.detail


@pytest.mark.asyncio
async def test_delete_user(user_service, test_user):
    """Test deleting a user"""
    # Execute
    result = await user_service.delete_user(test_user.user_id)
    
    # Assert
    assert result is True
    
    # Verify user is deleted
    with pytest.raises(HTTPException) as excinfo:
        await user_service.get_user(test_user.user_id)
    
    assert excinfo.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_user_not_found(user_service):
    """Test deleting a non-existent user"""
    # Execute & Assert
    with pytest.raises(HTTPException) as excinfo:
        await user_service.delete_user(uuid.uuid4())
    
    assert excinfo.value.status_code == 404
    assert "not found" in excinfo.value.detail


@pytest.mark.asyncio
async def test_get_or_create_user_existing(user_service, test_user):
    """Test getting an existing user by name"""
    # Execute
    user = await user_service.get_or_create_user(test_user.user_name)
    
    # Assert
    assert user is not None
    assert user.user_id == test_user.user_id
    assert user.user_name == test_user.user_name


@pytest.mark.asyncio
async def test_get_or_create_user_new(user_service):
    """Test creating a new user when not found by name"""
    # Execute
    user = await user_service.get_or_create_user("New User")
    
    # Assert
    assert user is not None
    assert user.user_id is not None
    assert user.user_name == "New User"
    assert user.created_at is not None


@pytest.mark.asyncio
async def test_get_or_create_user_no_name(user_service):
    """Test creating a new user with no name"""
    # Execute
    user = await user_service.get_or_create_user()
    
    # Assert
    assert user is not None
    assert user.user_id is not None
    assert user.user_name is None
    assert user.created_at is not None
