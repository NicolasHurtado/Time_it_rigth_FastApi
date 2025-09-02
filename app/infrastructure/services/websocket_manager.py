"""WebSocket connection manager for handling multiple client connections"""

import json
import logging
from typing import Any, Dict, List, Optional, Set

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections for real-time updates"""

    def __init__(self) -> None:
        # Store active connections by connection type
        self.connections: Dict[str, Set[WebSocket]] = {}
        # Store connection metadata
        self.connection_info: Dict[WebSocket, Dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket, connection_type: str, user_id: Optional[int] = None) -> None:
        """Accept a new WebSocket connection"""
        await websocket.accept()

        if connection_type not in self.connections:
            self.connections[connection_type] = set()

        self.connections[connection_type].add(websocket)
        self.connection_info[websocket] = {
            "type": connection_type,
            "user_id": user_id,
        }
        logger.info(f"WebSocket connected: {connection_type}, user_id: {user_id}")

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection"""
        if websocket in self.connection_info:
            connection_type = self.connection_info[websocket]["type"]
            user_id = self.connection_info[websocket]["user_id"]

            # Remove from connections set
            if connection_type in self.connections:
                self.connections[connection_type].discard(websocket)

                # Clean up empty connection types
                if not self.connections[connection_type]:
                    del self.connections[connection_type]

            # Remove connection info
            del self.connection_info[websocket]

            logger.info(f"WebSocket disconnected: {connection_type}, user_id: {user_id}")

    async def send_to_connection_type(self, connection_type: str, message: Dict[str, Any]) -> None:
        """Send message to all connections of a specific type"""
        if connection_type not in self.connections:
            return

        # Get connections and remove any that are closed
        connections = self.connections[connection_type].copy()
        disconnected = set()

        for connection in connections:
            try:
                await connection.send_text(json.dumps(message))
            except WebSocketDisconnect:
                disconnected.add(connection)
            except Exception as e:
                logger.error(f"Error sending message to WebSocket: {e}")
                disconnected.add(connection)

        # Clean up disconnected connections
        for connection in disconnected:
            self.disconnect(connection)

    async def send_to_user(self, user_id: int, message: Dict[str, Any]) -> None:
        """Send message to all connections for a specific user"""
        disconnected = set()

        for websocket, info in self.connection_info.items():
            if info["user_id"] == user_id:
                try:
                    await websocket.send_text(json.dumps(message))
                except WebSocketDisconnect:
                    disconnected.add(websocket)
                except Exception as e:
                    logger.error(f"Error sending message to user {user_id}: {e}")
                    disconnected.add(websocket)

        # Clean up disconnected connections
        for connection in disconnected:
            self.disconnect(connection)

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcast message to all active connections"""
        all_connections = set()
        for connections in self.connections.values():
            all_connections.update(connections)

        disconnected = set()

        for connection in all_connections:
            try:
                await connection.send_text(json.dumps(message))
            except WebSocketDisconnect:
                disconnected.add(connection)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")
                disconnected.add(connection)

        # Clean up disconnected connections
        for connection in disconnected:
            self.disconnect(connection)

    def get_connection_count(self, connection_type: str = None) -> int:
        """Get number of active connections"""
        if connection_type:
            return len(self.connections.get(connection_type, set()))

        total = 0
        for connections in self.connections.values():
            total += len(connections)
        return total

    def get_user_connections(self, user_id: int) -> List[WebSocket]:
        """Get all connections for a specific user"""
        user_connections = []
        for websocket, info in self.connection_info.items():
            if info["user_id"] == user_id:
                user_connections.append(websocket)
        return user_connections


# Global WebSocket manager instance
websocket_manager = WebSocketManager()
