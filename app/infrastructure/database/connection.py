"""Database connection and session management"""

from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings

# Convert SQLite URL to async format
async_database_url = settings.database_url.replace("sqlite:///", "sqlite+aiosqlite:///")

# Create async SQLite engine
async_engine = create_async_engine(
    async_database_url,
    poolclass=StaticPool,
    connect_args={
        "check_same_thread": False,
    },
    echo=settings.debug,
)

# Create sync engine for table creation
sync_engine = create_engine(
    settings.database_url,
    poolclass=StaticPool,
    connect_args={
        "check_same_thread": False,
    },
    echo=settings.debug,
)

# Create async session factory
AsyncSessionLocal = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

# Base class for all models
Base = declarative_base()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get async database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def create_tables() -> None:
    """Create all database tables (sync operation)"""
    Base.metadata.create_all(bind=sync_engine)


def drop_tables() -> None:
    """Drop all database tables (sync operation)"""
    Base.metadata.drop_all(bind=sync_engine)
