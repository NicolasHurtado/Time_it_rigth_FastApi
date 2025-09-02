"""Service for handling leaderboard update notifications"""

import logging
from typing import Any, Optional

from app.application.use_cases.game_use_cases import GetLeaderboardUseCase
from app.core.config import settings
from app.domain.interfaces.game_session_repository import GameSessionRepositoryInterface
from app.infrastructure.services.websocket_manager import websocket_manager
from app.presentation.schemas.game_schemas import LeaderboardEntry, LeaderboardResponse

logger = logging.getLogger(__name__)


class LeaderboardNotificationService:
    """Service to handle leaderboard update notifications via WebSocket"""

    def __init__(self, game_repository: GameSessionRepositoryInterface) -> None:
        self.game_repository = game_repository

    async def notify_leaderboard_update(self, updated_user_id: Optional[int] = None) -> None:
        """
        Notify all connected clients about leaderboard updates

        Args:
            updated_user_id: ID of user whose game completion triggered the update
        """
        try:
            logger.info(f"Notifying leaderboard update for user {updated_user_id}")
            # Get updated leaderboard data
            leaderboard_use_case = GetLeaderboardUseCase(self.game_repository)
            leaderboard_data = await leaderboard_use_case.execute(
                limit=settings.leaderboard_top_count
            )

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

            leaderboard_response = LeaderboardResponse(
                leaderboard=enhanced_entries, total_entries=len(enhanced_entries)
            )

            logger.info(f"Leaderboard response: {leaderboard_response}")

            # Create WebSocket message
            message = {
                "type": "leaderboard_update",
                "data": leaderboard_response.model_dump(),
                "timestamp": self._get_current_timestamp(),
                "triggered_by_user": updated_user_id,
            }

            # Send to all leaderboard subscribers
            connection_count = websocket_manager.get_connection_count("leaderboard")
            logger.info(
                f"Sending leaderboard update to {connection_count} connected WebSocket clients"
            )

            await websocket_manager.send_to_connection_type("leaderboard", message)

            logger.info(
                f"✅ Leaderboard update notification sent successfully to {connection_count} clients"
            )

        except Exception as e:
            logger.error(f"Error sending leaderboard update notification: {e}")

    async def notify_user_rank_change(self, user_id: int, new_rank: int, old_rank: Optional[int] = None) -> None:
        """
        Notify a specific user about their rank change

        Args:
            user_id: User whose rank changed
            new_rank: New rank position
            old_rank: Previous rank position (if known)
        """
        try:
            message = {
                "type": "rank_change",
                "data": {
                    "user_id": user_id,
                    "new_rank": new_rank,
                    "old_rank": old_rank,
                    "improved": old_rank is not None and new_rank < old_rank,
                },
                "timestamp": self._get_current_timestamp(),
            }

            # Send to specific user
            await websocket_manager.send_to_user(user_id, message)

            logger.info(
                f"Rank change notification sent to user {user_id}: {old_rank} -> {new_rank}"
            )

        except Exception as e:
            logger.error(f"Error sending rank change notification to user {user_id}: {e}")

    async def notify_new_high_score(self, user_id: int, username: str, deviation_ms: int) -> None:
        """
        Notify all clients about a new high score (best deviation)

        Args:
            user_id: User who achieved the score
            username: Username of the user
            deviation_ms: The deviation that achieved the high score
        """
        try:
            message = {
                "type": "new_high_score",
                "data": {
                    "user_id": user_id,
                    "username": username,
                    "deviation_ms": deviation_ms,
                    "accuracy_percentage": round(
                        max(0, 100 * (1 - (deviation_ms / settings.target_time_ms))), 2
                    ),
                },
                "timestamp": self._get_current_timestamp(),
            }

            # Broadcast to all leaderboard subscribers
            await websocket_manager.send_to_connection_type("leaderboard", message)

            logger.info(
                f"New high score notification sent: {username} with {deviation_ms}ms deviation"
            )

        except Exception as e:
            logger.error(f"Error sending new high score notification: {e}")

    async def send_connection_status(self, websocket: Any) -> None:
        """Send initial connection status and current leaderboard to new connection"""
        try:
            # Get current leaderboard
            leaderboard_use_case = GetLeaderboardUseCase(self.game_repository)
            leaderboard_data = await leaderboard_use_case.execute(
                limit=settings.leaderboard_top_count
            )

            # Enhance leaderboard entries
            enhanced_entries = []
            for entry in leaderboard_data:
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

            leaderboard_response = LeaderboardResponse(
                leaderboard=enhanced_entries, total_entries=len(enhanced_entries)
            )

            # Send welcome message with current leaderboard
            welcome_message = {
                "type": "connection_established",
                "data": {
                    "message": "Connected to leaderboard updates",
                    "current_leaderboard": leaderboard_response.model_dump(),
                    "active_connections": websocket_manager.get_connection_count("leaderboard"),
                },
                "timestamp": self._get_current_timestamp(),
            }

            await websocket.send_text(str(welcome_message).replace("'", '"'))

        except Exception as e:
            logger.error(f"Error sending connection status: {e}")

    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime

        return datetime.utcnow().isoformat() + "Z"
