"""Game session API endpoints"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases.game_use_cases import (
    GetActiveSessionUseCase,
    GetUserGameHistoryUseCase,
    StartGameUseCase,
    StopGameUseCase,
)
from app.core.config import settings
from app.core.dependencies import get_current_active_user
from app.domain.value_objects.deviation import Deviation
from app.domain.value_objects.duration import Duration
from app.infrastructure.database.connection import get_async_db
from app.infrastructure.database.models import User
from app.infrastructure.repositories.game_session_repository import GameSessionRepository
from app.infrastructure.services.leaderboard_notification_service import (
    LeaderboardNotificationService,
)
from app.presentation.schemas.game_schemas import (
    GameSessionResponse,
    StartGameResponse,
    StopGameResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/start",
    response_model=StartGameResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start new game session",
    description="Begin a new timer game session. User must stop timer at exactly 10 seconds.",
)
async def start_game(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> StartGameResponse:
    """Start a new game session"""
    try:
        game_repository = GameSessionRepository(db)
        start_game_use_case = StartGameUseCase(game_repository)

        session = await start_game_use_case.execute(current_user.id)

        return StartGameResponse(
            session_id=session.id,
            start_time=session.start_time,
            target_time_ms=settings.target_time_ms,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while starting the game",
        )


@router.post(
    "/{session_id}/stop",
    response_model=StopGameResponse,
    summary="Stop game session",
    description="End the game session and calculate timing accuracy",
)
async def stop_game(
    session_id: int = Path(..., description="Game session ID"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> StopGameResponse:
    """Stop a game session and calculate results"""
    try:
        logger.info(f"Stopping game session {session_id} for user {current_user.id}")
        game_repository = GameSessionRepository(db)
        stop_game_use_case = StopGameUseCase(game_repository)

        session = await stop_game_use_case.execute(session_id, current_user.id)

        actual_duration = Duration.from_seconds((session.duration_ms or 0) / 1000)
        target_duration = Duration.from_seconds(settings.target_time_ms / 1000)
        deviation = Deviation.from_durations(actual_duration, target_duration)

        # Send leaderboard update notification if game was completed successfully
        if session.is_completed and session.deviation_ms is not None:
            try:
                logger.info(f"Sending leaderboard update notification for session {session.id}")
                notification_service = LeaderboardNotificationService(game_repository)

                # Notify general leaderboard update
                await notification_service.notify_leaderboard_update(current_user.id)

                # Check if this is a new personal best or high score
                logger.info(
                    f"Checking if this is a new personal best or high score for user {current_user.id}"
                )
                user_sessions = await game_repository.get_by_user(current_user.id, limit=100)
                completed_sessions = [
                    s for s in user_sessions if s.is_completed and s.deviation_ms is not None
                ]

                if completed_sessions:
                    # Filter out None values and get minimum deviation
                    valid_deviations = [s.deviation_ms for s in completed_sessions if s.deviation_ms is not None]
                    if valid_deviations:
                        best_deviation = min(valid_deviations)
                        if session.deviation_ms == best_deviation:
                            # This is a new personal best, check if it's also a global high score
                            logger.info(
                                "This is a new personal best, checking if it's also a global high score"
                            )
                            leaderboard_data = await game_repository.get_leaderboard(limit=1)
                            if (
                                leaderboard_data
                                and session.deviation_ms <= leaderboard_data[0]["best_deviation_ms"]
                            ):
                                await notification_service.notify_new_high_score(
                                    current_user.id, current_user.username, session.deviation_ms
                                )

            except Exception as e:
                # Log error but don't fail the game completion
                logger.error(f"Error sending leaderboard notifications: {e}")

        # Create response message based on performance
        if deviation.is_perfect():
            message = "PERFECT! Exactly 10 seconds!"
        elif deviation.is_excellent():
            message = f"Excellent! Only {deviation.milliseconds}ms off target."
        elif deviation.is_good():
            message = f"Good timing! You were {deviation.milliseconds}ms off target."
        else:
            message = f"You were {deviation.milliseconds}ms off target. Try again!"

        return StopGameResponse(
            session_id=session.id,
            duration_ms=session.duration_ms,
            deviation_ms=session.deviation_ms,
            accuracy_score=session.get_accuracy_score(),
            grade=deviation.get_grade(),
            message=message,
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while stopping the game",
        )


@router.get(
    "/history",
    response_model=List[GameSessionResponse],
    summary="Get user's game history",
    description="Get current user's game session history",
)
async def get_game_history(
    limit: int = 10,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> List[GameSessionResponse]:
    """Get user's game history"""
    try:
        game_repository = GameSessionRepository(db)
        history_use_case = GetUserGameHistoryUseCase(game_repository)

        sessions = await history_use_case.execute(current_user.id, limit)

        return [
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

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching game history",
        )


@router.get(
    "/active",
    response_model=GameSessionResponse,
    summary="Get active game session",
    description="Get current user's active game session if any",
)
async def get_active_session(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> GameSessionResponse | None:
    """Get user's active session"""
    try:
        game_repository = GameSessionRepository(db)
        active_session_use_case = GetActiveSessionUseCase(game_repository)

        session = await active_session_use_case.execute(current_user.id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="No active session found"
            )

        return GameSessionResponse(
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

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching active session",
        )
