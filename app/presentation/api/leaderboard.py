"""Leaderboard API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases.game_use_cases import GetLeaderboardUseCase
from app.core.config import settings
from app.infrastructure.database.connection import get_async_db
from app.infrastructure.repositories.game_session_repository import GameSessionRepository
from app.presentation.schemas.game_schemas import LeaderboardEntry, LeaderboardResponse

router = APIRouter()


@router.get(
    "",
    response_model=LeaderboardResponse,
    summary="Get leaderboard",
    description="Get top players ranked by average deviation from 10-second target",
)
async def get_leaderboard(
    limit: int = Query(
        default=settings.leaderboard_top_count,
        ge=1,
        le=100,
        description="Number of top players to return (1-100)",
    ),
    db: AsyncSession = Depends(get_async_db),
) -> LeaderboardResponse:
    """Get leaderboard with top players"""
    try:
        game_repository = GameSessionRepository(db)
        leaderboard_use_case = GetLeaderboardUseCase(game_repository)

        leaderboard_data = await leaderboard_use_case.execute(limit)

        # Enhance leaderboard entries with accuracy percentage
        enhanced_entries = []
        for entry in leaderboard_data:
            # Calculate accuracy percentage from average deviation
            accuracy_percentage = max(
                0, 100 * (1 - (entry["avg_deviation_ms"] / settings.target_time_ms))
            )

            enhanced_entries.append(
                LeaderboardEntry(
                    rank=entry["rank"],
                    user_id=entry["user_id"],
                    username=entry["username"],
                    avg_deviation_ms=entry["avg_deviation_ms"],
                    best_deviation_ms=entry["best_deviation_ms"],
                    total_games=entry["total_games"],
                    accuracy_percentage=round(accuracy_percentage, 2),
                )
            )

        return LeaderboardResponse(
            leaderboard=enhanced_entries, total_entries=len(enhanced_entries)
        )

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching leaderboard",
        )
