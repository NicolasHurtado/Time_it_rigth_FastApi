"""User repository interface"""

from abc import ABC, abstractmethod
from typing import Optional

from app.domain.entities.user import UserEntity


class UserRepositoryInterface(ABC):
    """Interface for user repository"""

    @abstractmethod
    async def create(self, user: UserEntity) -> UserEntity:
        """Create a new user"""
        pass

    @abstractmethod
    async def get_by_id(self, user_id: int) -> Optional[UserEntity]:
        """Get user by ID"""
        pass

    @abstractmethod
    async def get_by_username(self, username: str) -> Optional[UserEntity]:
        """Get user by username"""
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[UserEntity]:
        """Get user by email"""
        pass

    @abstractmethod
    async def update(self, user: UserEntity) -> UserEntity:
        """Update user"""
        pass

    @abstractmethod
    async def delete(self, user_id: int) -> bool:
        """Delete user"""
        pass
