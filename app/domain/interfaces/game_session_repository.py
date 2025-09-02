"""Game session repository interface"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from app.domain.entities.game_session import GameSessionEntity


class GameSessionRepositoryInterface(ABC):
    """Interface for game session repository"""

    @abstractmethod
    async def create(self, session: GameSessionEntity) -> GameSessionEntity:
        """Create a new game session"""
        pass

    @abstractmethod
    async def get_by_id(self, session_id: int) -> Optional[GameSessionEntity]:
        """Get session by ID"""
        pass

    @abstractmethod
    async def get_active_by_user(self, user_id: int) -> Optional[GameSessionEntity]:
        """Get active session for user"""
        pass

    @abstractmethod
    async def get_by_user(self, user_id: int, limit: int = 10) -> List[GameSessionEntity]:
        """Get sessions by user"""
        pass

    @abstractmethod
    async def update(self, session: GameSessionEntity) -> GameSessionEntity:
        """Update session"""
        pass

    @abstractmethod
    async def get_leaderboard(self, limit: int = 10) -> List[dict]:
        """Get leaderboard data"""
        pass

    @abstractmethod
    async def expire_old_sessions(self, cutoff_time: datetime) -> int:
        """Expire old active sessions"""
        pass
