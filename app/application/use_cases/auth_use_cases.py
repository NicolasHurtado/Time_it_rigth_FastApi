"""Authentication use cases"""

from typing import Optional

from app.core.security import create_token_for_user, get_password_hash, verify_password
from app.domain.entities.user import UserEntity
from app.domain.interfaces.user_repository import UserRepositoryInterface


class RegisterUserUseCase:
    """Use case for user registration"""

    def __init__(self, user_repository: UserRepositoryInterface):
        self.user_repository = user_repository

    async def execute(self, username: str, email: str, password: str) -> UserEntity:
        """Register a new user"""
        # Check if user already exists
        existing_user = await self.user_repository.get_by_username(username)
        if existing_user:
            raise ValueError("Username already exists")

        existing_email = await self.user_repository.get_by_email(email)
        if existing_email:
            raise ValueError("Email already exists")

        # Create user entity
        user_entity = UserEntity(
            id=None,
            username=username,
            email=email,
            password_hash=get_password_hash(password),
        )

        # Validate user data
        if not user_entity.is_valid_username():
            raise ValueError("Invalid username format")

        if not user_entity.is_valid_email():
            raise ValueError("Invalid email format")

        # Save user
        return await self.user_repository.create(user_entity)


class LoginUserUseCase:
    """Use case for user login"""

    def __init__(self, user_repository: UserRepositoryInterface):
        self.user_repository = user_repository

    async def execute(self, username: str, password: str) -> dict:
        """Authenticate user and return token"""
        # Get user by username
        user = await self.user_repository.get_by_username(username)
        if not user:
            raise ValueError("Invalid credentials")

        # Verify password
        if not verify_password(password, user.password_hash):
            raise ValueError("Invalid credentials")

        # Create access token
        access_token = create_token_for_user(user.id, user.username)

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "created_at": user.created_at,
                "updated_at": user.updated_at,
            },
        }


class GetUserProfileUseCase:
    """Use case for getting user profile"""

    def __init__(self, user_repository: UserRepositoryInterface):
        self.user_repository = user_repository

    async def execute(self, user_id: int) -> Optional[UserEntity]:
        """Get user profile by ID"""
        return await self.user_repository.get_by_id(user_id)
