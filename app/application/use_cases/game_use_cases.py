"""Game session use cases"""

from datetime import datetime, timedelta
from typing import List, Optional

from app.core.config import settings
from app.domain.entities.game_session import GameSessionEntity, SessionStatus
from app.domain.interfaces.game_session_repository import GameSessionRepositoryInterface


class StartGameUseCase:
    """Use case for starting a game session"""

    def __init__(self, game_repository: GameSessionRepositoryInterface):
        self.game_repository = game_repository

    async def execute(self, user_id: int) -> GameSessionEntity:
        """Start a new game session"""
        # Check if user already has an active session
        existing_session = await self.game_repository.get_active_by_user(user_id)
        if existing_session:
            # Check if session should be expired
            if existing_session.is_expired():
                existing_session.expire_session()
                await self.game_repository.update(existing_session)
            else:
                raise ValueError("User already has an active game session")

        # Create new session
        session_entity = GameSessionEntity(
            id=None,
            user_id=user_id,
            start_time=datetime.utcnow(),
            status=SessionStatus.ACTIVE,
        )

        return await self.game_repository.create(session_entity)


class StopGameUseCase:
    """Use case for stopping a game session"""

    def __init__(self, game_repository: GameSessionRepositoryInterface):
        self.game_repository = game_repository

    async def execute(self, session_id: int, user_id: int) -> GameSessionEntity:
        """Stop a game session and calculate results"""
        # Get session
        session = await self.game_repository.get_by_id(session_id)
        if not session:
            raise ValueError("Session not found")

        # Verify ownership
        if session.user_id != user_id:
            raise ValueError("Session does not belong to user")

        # Check session status
        if not session.is_active:
            raise ValueError("Session is not active")

        # Check if session is expired
        if session.is_expired():
            session.expire_session()
            await self.game_repository.update(session)
            raise ValueError("Session has expired")

        # Complete session
        stop_time = datetime.utcnow()
        session.complete_session(stop_time)

        return await self.game_repository.update(session)


class GetUserGameHistoryUseCase:
    """Use case for getting user's game history"""

    def __init__(self, game_repository: GameSessionRepositoryInterface):
        self.game_repository = game_repository

    async def execute(self, user_id: int, limit: int = 10) -> List[GameSessionEntity]:
        """Get user's game history"""
        return await self.game_repository.get_by_user(user_id, limit)


class GetLeaderboardUseCase:
    """Use case for getting leaderboard"""

    def __init__(self, game_repository: GameSessionRepositoryInterface):
        self.game_repository = game_repository

    async def execute(self, limit: int = 10) -> List[dict]:
        """Get leaderboard data"""
        return await self.game_repository.get_leaderboard(limit)


class ExpireOldSessionsUseCase:
    """Use case for expiring old sessions (background task)"""

    def __init__(self, game_repository: GameSessionRepositoryInterface):
        self.game_repository = game_repository

    async def execute(self) -> int:
        """Expire sessions older than configured time"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=settings.session_expire_minutes)
        return await self.game_repository.expire_old_sessions(cutoff_time)


class GetActiveSessionUseCase:
    """Use case for getting user's active session"""

    def __init__(self, game_repository: GameSessionRepositoryInterface):
        self.game_repository = game_repository

    async def execute(self, user_id: int) -> Optional[GameSessionEntity]:
        """Get user's active session if any"""
        session = await self.game_repository.get_active_by_user(user_id)

        # Check if session should be expired
        if session and session.is_expired():
            session.expire_session()
            await self.game_repository.update(session)
            return None

        return session
