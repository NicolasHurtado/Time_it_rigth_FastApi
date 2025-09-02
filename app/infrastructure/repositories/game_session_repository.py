"""Game session repository implementation"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.domain.entities.game_session import GameSessionEntity, SessionStatus
from app.domain.interfaces.game_session_repository import GameSessionRepositoryInterface
from app.infrastructure.database.models import GameSession, User


class GameSessionRepository(GameSessionRepositoryInterface):
    """Async SQLAlchemy implementation of game session repository"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, session_entity: GameSessionEntity) -> GameSessionEntity:
        """Create a new game session"""
        db_session = GameSession(
            user_id=session_entity.user_id,
            start_time=session_entity.start_time,
            status=session_entity.status.value,
        )

        self.db.add(db_session)
        await self.db.commit()
        await self.db.refresh(db_session)

        return self._to_entity(db_session)

    async def get_by_id(self, session_id: int) -> Optional[GameSessionEntity]:
        """Get session by ID"""
        stmt = select(GameSession).where(GameSession.id == session_id)
        result = await self.db.execute(stmt)
        db_session = result.scalar_one_or_none()
        return self._to_entity(db_session) if db_session else None

    async def get_active_by_user(self, user_id: int) -> Optional[GameSessionEntity]:
        """Get active session for user"""
        stmt = select(GameSession).where(
            GameSession.user_id == user_id,
            GameSession.status == SessionStatus.ACTIVE.value,
        )
        result = await self.db.execute(stmt)
        db_session = result.scalar_one_or_none()
        return self._to_entity(db_session) if db_session else None

    async def get_by_user(self, user_id: int, limit: int = 10) -> List[GameSessionEntity]:
        """Get sessions by user"""
        stmt = (
            select(GameSession)
            .where(GameSession.user_id == user_id)
            .order_by(desc(GameSession.created_at))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        db_sessions = result.scalars().all()

        return [self._to_entity(session) for session in db_sessions]

    async def update(self, session_entity: GameSessionEntity) -> GameSessionEntity:
        """Update session"""
        stmt = select(GameSession).where(GameSession.id == session_entity.id)
        result = await self.db.execute(stmt)
        db_session = result.scalar_one_or_none()

        if not db_session:
            raise ValueError("Session not found")

        db_session.stop_time = session_entity.stop_time
        db_session.duration_ms = session_entity.duration_ms
        db_session.deviation_ms = session_entity.deviation_ms
        db_session.status = session_entity.status.value

        await self.db.commit()
        await self.db.refresh(db_session)

        return self._to_entity(db_session)

    async def get_leaderboard(self, limit: int = 10) -> List[dict]:
        """Get leaderboard data"""
        # Calculate average deviation, best deviation for each user with completed games
        stmt = (
            select(
                User.id,
                User.username,
                func.avg(GameSession.deviation_ms).label("avg_deviation"),
                func.min(GameSession.deviation_ms).label("best_deviation"),
                func.count(GameSession.id).label("total_games"),
            )
            .join(GameSession, User.id == GameSession.user_id)
            .where(
                GameSession.status == SessionStatus.COMPLETED.value,
                GameSession.deviation_ms.isnot(None),
            )
            .group_by(User.id, User.username)
            .order_by(func.avg(GameSession.deviation_ms))
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        leaderboard = result.fetchall()

        return [
            {
                "user_id": row.id,
                "username": row.username,
                "avg_deviation_ms": round(row.avg_deviation, 2),
                "best_deviation_ms": int(row.best_deviation),
                "total_games": row.total_games,
                "rank": idx + 1,
            }
            for idx, row in enumerate(leaderboard)
        ]

    async def expire_old_sessions(self, cutoff_time: datetime) -> int:
        """Expire old active sessions"""
        stmt = select(GameSession).where(
            GameSession.status == SessionStatus.ACTIVE.value,
            GameSession.start_time < cutoff_time,
        )
        result = await self.db.execute(stmt)
        sessions_to_expire = result.scalars().all()

        expired_count = 0
        for session in sessions_to_expire:
            session.status = SessionStatus.EXPIRED.value
            expired_count += 1

        await self.db.commit()
        return expired_count

    def _to_entity(self, db_session: GameSession) -> GameSessionEntity:
        """Convert database model to domain entity"""
        return GameSessionEntity(
            id=db_session.id,
            user_id=db_session.user_id,
            start_time=db_session.start_time,
            stop_time=db_session.stop_time,
            duration_ms=db_session.duration_ms,
            deviation_ms=db_session.deviation_ms,
            status=SessionStatus(db_session.status),
            created_at=db_session.created_at,
        )
