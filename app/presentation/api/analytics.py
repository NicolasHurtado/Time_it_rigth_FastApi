"""User analytics API endpoints"""


from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.application.use_cases.game_use_cases import GetUserGameHistoryUseCase
from app.core.dependencies import get_current_active_user
from app.domain.entities.game_session import SessionStatus
from app.infrastructure.database.connection import get_async_db
from app.infrastructure.database.models import GameSession, User
from app.infrastructure.repositories.game_session_repository import GameSessionRepository
from app.infrastructure.repositories.user_repository import UserRepository
from app.presentation.schemas.game_schemas import GameSessionResponse, UserStatsResponse

router = APIRouter()


@router.get(
    "/user/{user_id}",
    response_model=UserStatsResponse,
    summary="Get user statistics",
    description="Get detailed statistics for a specific user",
)
async def get_user_analytics(
    user_id: int = Path(..., description="User ID"),
    limit: int = 20,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> UserStatsResponse:
    """Get user analytics and statistics"""
    try:
        # Users can only view their own analytics for privacy
        if user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own statistics",
            )

        user_repository = UserRepository(db)
        game_repository = GameSessionRepository(db)

        # Get user
        user = await user_repository.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # Get user's game history
        history_use_case = GetUserGameHistoryUseCase(game_repository)
        sessions = await history_use_case.execute(user_id, limit)

        # Calculate statistics from database
        stats_stmt = select(
            func.count(GameSession.id).label("total_games"),
            func.count(func.nullif(GameSession.status, SessionStatus.ACTIVE.value)).label(
                "completed_games"
            ),
            func.avg(GameSession.deviation_ms).label("avg_deviation"),
            func.min(GameSession.deviation_ms).label("best_deviation"),
        ).where(
            GameSession.user_id == user_id,
            GameSession.status == SessionStatus.COMPLETED.value,
        )
        stats_result = await db.execute(stats_stmt)
        stats_query = stats_result.first()

        total_games = len([s for s in sessions])
        completed_games = len([s for s in sessions if s.is_completed])
        avg_deviation = (
            stats_query.avg_deviation if stats_query and stats_query.avg_deviation else None
        )
        best_deviation = (
            int(stats_query.best_deviation) if stats_query and stats_query.best_deviation else None
        )

        # Calculate average accuracy
        avg_accuracy = None
        if avg_deviation is not None:
            avg_accuracy = max(0, 100 * (1 - (avg_deviation / 10000)))  # 10000ms = target
            avg_accuracy = round(avg_accuracy, 2)

        # Convert sessions to response format
        games_history = [
            GameSessionResponse(
                id=session.id,
                user_id=session.user_id,
                start_time=session.start_time,
                stop_time=session.stop_time,
                duration_ms=session.duration_ms,
                deviation_ms=session.deviation_ms,
                status=session.status.value,
                created_at=session.created_at,
                accuracy_score=session.get_accuracy_score() if session.is_completed else None,
            )
            for session in sessions
        ]

        return UserStatsResponse(
            user_id=user.id,
            username=user.username,
            total_games=total_games,
            completed_games=completed_games,
            avg_deviation_ms=float(avg_deviation) if avg_deviation else None,
            best_deviation_ms=best_deviation,
            avg_accuracy=avg_accuracy,
            games_history=games_history,
        )

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching user analytics",
        )


@router.get(
    "/me",
    response_model=UserStatsResponse,
    summary="Get my statistics",
    description="Get current user's detailed statistics",
)
async def get_my_analytics(
    limit: int = 20,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> UserStatsResponse:
    """Get current user's analytics"""
    return await get_user_analytics(current_user.id, limit, current_user, db)
