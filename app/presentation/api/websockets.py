"""WebSocket endpoints for real-time updates"""

import json
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.infrastructure.database.connection import get_async_db
from app.infrastructure.repositories.game_session_repository import GameSessionRepository
from app.infrastructure.services.leaderboard_notification_service import (
    LeaderboardNotificationService,
)
from app.infrastructure.services.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/leaderboard")
async def websocket_leaderboard_endpoint(
    websocket: WebSocket,
    user_id: Optional[int] = Query(None, description="Optional user ID for personalized updates"),
) -> None:
    """
    WebSocket endpoint for real-time leaderboard updates

    Clients can connect to receive live updates when:
    - New games are completed
    - Leaderboard rankings change
    - New high scores are achieved
    """
    # Get database session for this connection
    db_generator = get_async_db()
    db = await db_generator.__anext__()
    try:
        try:
            # Connect to WebSocket manager
            await websocket_manager.connect(websocket, "leaderboard", user_id)

            # Create notification service
            game_repository = GameSessionRepository(db)
            notification_service = LeaderboardNotificationService(game_repository)

            # Send initial connection status and current leaderboard
            await notification_service.send_connection_status(websocket)

            logger.info(f"New leaderboard WebSocket connection established for user: {user_id}")

            # Keep connection alive and handle incoming messages
            while True:
                try:
                    # Wait for messages from client
                    data = await websocket.receive_text()
                    message = json.loads(data)

                    # Handle different message types from client
                    await handle_client_message(websocket, message, notification_service, user_id)

                except json.JSONDecodeError:
                    # Send error message for invalid JSON
                    error_message = {
                        "type": "error",
                        "data": {"message": "Invalid JSON format"},
                        "timestamp": notification_service._get_current_timestamp(),
                    }
                    await websocket.send_text(json.dumps(error_message))

        except WebSocketDisconnect:
            logger.info(f"Leaderboard WebSocket disconnected for user: {user_id}")
        except Exception as e:
            logger.error(f"Error in leaderboard WebSocket connection: {e}")
        finally:
            # Clean up connection
            websocket_manager.disconnect(websocket)
    finally:
        await db.close()


async def handle_client_message(
    websocket: WebSocket,
    message: Dict[str, Any],
    notification_service: LeaderboardNotificationService,
    user_id: Optional[int],
) -> None:
    """Handle messages received from WebSocket clients"""
    try:
        message_type = message.get("type", "")

        if message_type == "ping":
            # Respond to ping with pong
            pong_message = {
                "type": "pong",
                "data": {"message": "Connection alive"},
                "timestamp": notification_service._get_current_timestamp(),
            }
            await websocket.send_text(json.dumps(pong_message))

        elif message_type == "request_leaderboard":
            # Send current leaderboard data
            await notification_service.send_connection_status(websocket)

        elif message_type == "subscribe_user_updates":
            # Client wants to subscribe to updates for a specific user
            target_user_id = message.get("data", {}).get("user_id")
            if target_user_id:
                # Update connection info to include subscription
                if websocket in websocket_manager.connection_info:
                    websocket_manager.connection_info[websocket][
                        "subscribed_user_id"
                    ] = target_user_id

                response = {
                    "type": "subscription_confirmed",
                    "data": {
                        "message": f"Subscribed to updates for user {target_user_id}",
                        "user_id": target_user_id,
                    },
                    "timestamp": notification_service._get_current_timestamp(),
                }
                await websocket.send_text(json.dumps(response))

        else:
            # Unknown message type
            error_message = {
                "type": "error",
                "data": {"message": f"Unknown message type: {message_type}"},
                "timestamp": notification_service._get_current_timestamp(),
            }
            await websocket.send_text(json.dumps(error_message))

    except Exception as e:
        logger.error(f"Error handling client message: {e}")
        error_message = {
            "type": "error",
            "data": {"message": "Error processing message"},
            "timestamp": notification_service._get_current_timestamp(),
        }
        await websocket.send_text(json.dumps(error_message))


@router.get("/connections/status")
async def get_websocket_status() -> Dict[str, Any]:
    """Get current WebSocket connection status"""
    return {
        "leaderboard_connections": websocket_manager.get_connection_count("leaderboard"),
        "total_connections": websocket_manager.get_connection_count(),
        "connection_types": list(websocket_manager.connections.keys()),
    }
