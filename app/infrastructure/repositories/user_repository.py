"""User repository implementation"""

from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.domain.entities.user import UserEntity
from app.domain.interfaces.user_repository import UserRepositoryInterface
from app.infrastructure.database.models import User


class UserRepository(UserRepositoryInterface):
    """Async SQLAlchemy implementation of user repository"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_entity: UserEntity) -> UserEntity:
        """Create a new user"""
        db_user = User(
            username=user_entity.username,
            email=user_entity.email,
            password_hash=user_entity.password_hash,
        )

        try:
            self.db.add(db_user)
            await self.db.commit()
            await self.db.refresh(db_user)

            return self._to_entity(db_user)
        except IntegrityError:
            await self.db.rollback()
            raise ValueError("Username or email already exists")

    async def get_by_id(self, user_id: int) -> Optional[UserEntity]:
        """Get user by ID"""
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        db_user = result.scalar_one_or_none()
        return self._to_entity(db_user) if db_user else None

    async def get_by_username(self, username: str) -> Optional[UserEntity]:
        """Get user by username"""
        stmt = select(User).where(User.username == username)
        result = await self.db.execute(stmt)
        db_user = result.scalar_one_or_none()
        return self._to_entity(db_user) if db_user else None

    async def get_by_email(self, email: str) -> Optional[UserEntity]:
        """Get user by email"""
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        db_user = result.scalar_one_or_none()
        return self._to_entity(db_user) if db_user else None

    async def update(self, user_entity: UserEntity) -> UserEntity:
        """Update user"""
        stmt = select(User).where(User.id == user_entity.id)
        result = await self.db.execute(stmt)
        db_user = result.scalar_one_or_none()

        if not db_user:
            raise ValueError("User not found")

        db_user.username = user_entity.username
        db_user.email = user_entity.email
        db_user.password_hash = user_entity.password_hash

        await self.db.commit()
        await self.db.refresh(db_user)

        return self._to_entity(db_user)

    async def delete(self, user_id: int) -> bool:
        """Delete user"""
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        db_user = result.scalar_one_or_none()

        if not db_user:
            return False

        await self.db.delete(db_user)
        await self.db.commit()
        return True

    def _to_entity(self, db_user: User) -> UserEntity:
        """Convert database model to domain entity"""
        return UserEntity(
            id=db_user.id,
            username=db_user.username,
            email=db_user.email,
            password_hash=db_user.password_hash,
            created_at=db_user.created_at,
            updated_at=db_user.updated_at,
        )
