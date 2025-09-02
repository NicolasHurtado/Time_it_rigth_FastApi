"""SQLAlchemy database models"""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.infrastructure.database.connection import Base


class User(Base):
    """User model"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship with game sessions
    game_sessions = relationship("GameSession", back_populates="user")


class GameSession(Base):
    """Game session model"""

    __tablename__ = "game_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    stop_time = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)  # Duration in milliseconds
    deviation_ms = Column(Integer, nullable=True)  # Deviation from target (10000ms)
    status = Column(String(20), default="active")  # active, completed, expired
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship with user
    user = relationship("User", back_populates="game_sessions")

    def is_completed(self) -> bool:
        """Check if session is completed"""
        return str(self.status) == "completed"

    def is_active(self) -> bool:
        """Check if session is active"""
        return str(self.status) == "active"

    def is_expired(self) -> bool:
        """Check if session is expired"""
        return str(self.status) == "expired"
