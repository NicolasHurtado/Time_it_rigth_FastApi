"""Tests for WebSocket functionality and real-time leaderboard updates"""

import json
from datetime import datetime
from typing import AsyncGenerator, Dict, List, Any
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from websockets.exceptions import ConnectionClosedError

from app.core.security import create_token_for_user, get_password_hash
from app.infrastructure.database.connection import Base, get_async_db
from app.infrastructure.database.models import GameSession, User
from app.infrastructure.repositories.game_session_repository import GameSessionRepository
from app.infrastructure.services.leaderboard_notification_service import (
    LeaderboardNotificationService,
)
from app.infrastructure.services.websocket_manager import WebSocketManager
from app.main import create_application

# Create app instance for testing
app = create_application()


class MockWebSocket:
    """Mock WebSocket for testing"""

    def __init__(self) -> None:
        self.messages_sent: List[str] = []
        self.is_closed = False
        self.receive_queue: List[str] = []

    async def send_text(self, message: str) -> None:
        """Mock send_text method"""
        if self.is_closed:
            raise ConnectionClosedError(None, None)
        self.messages_sent.append(message)

    async def receive_text(self) -> str:
        """Mock receive_text method"""
        if self.is_closed:
            raise ConnectionClosedError(None, None)
        if self.receive_queue:
            return self.receive_queue.pop(0)
        return '{"type": "ping"}'  # Default message

    async def accept(self) -> None:
        """Mock accept method"""
        pass

    def close(self) -> None:
        """Mock close method"""
        self.is_closed = True

    def add_message_to_queue(self, message: str) -> None:
        """Add message to receive queue"""
        self.receive_queue.append(message)


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
)
TestingAsyncSessionLocal = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Override async database dependency for testing"""
    async with TestingAsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# Override the dependency
app.dependency_overrides[get_async_db] = override_get_async_db


@pytest_asyncio.fixture
async def async_session() -> AsyncGenerator[AsyncSession, None]:
    """Create async test session"""
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingAsyncSessionLocal() as session:
        yield session

    # Drop tables after test
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def test_users(async_session: AsyncSession) -> List[User]:
    """Create test users"""
    users = [
        User(
            username="pro_player",
            email="pro@test.com",
            password_hash=get_password_hash("testpass123"),
        ),
        User(
            username="casual_player",
            email="casual@test.com",
            password_hash=get_password_hash("testpass123"),
        ),
    ]

    async_session.add_all(users)
    await async_session.commit()

    for user in users:
        await async_session.refresh(user)

    return users


@pytest_asyncio.fixture
async def game_sessions(async_session: AsyncSession, test_users: List[User]) -> List[GameSession]:
    """Create test game sessions"""
    sessions = [
        GameSession(
            user_id=test_users[0].id,
            start_time=datetime.utcnow(),
            stop_time=datetime.utcnow(),
            duration_ms=9950,
            deviation_ms=50,
            status="completed",
        ),
        GameSession(
            user_id=test_users[1].id,
            start_time=datetime.utcnow(),
            stop_time=datetime.utcnow(),
            duration_ms=10200,
            deviation_ms=200,
            status="completed",
        ),
    ]

    async_session.add_all(sessions)
    await async_session.commit()

    for session in sessions:
        await async_session.refresh(session)

    return sessions


class TestWebSocketManager:
    """Tests for WebSocket manager functionality"""

    def setup_method(self) -> None:
        """Set up fresh WebSocket manager for each test"""
        self.manager = WebSocketManager()

    @pytest.mark.asyncio
    async def test_connect_websocket(self) -> None:
        """Test WebSocket connection"""
        mock_ws = MockWebSocket()

        await self.manager.connect(mock_ws, "leaderboard", user_id=123)

        assert "leaderboard" in self.manager.connections
        assert mock_ws in self.manager.connections["leaderboard"]
        assert mock_ws in self.manager.connection_info
        assert self.manager.connection_info.get(mock_ws, {}).get("type") == "leaderboard"
        assert self.manager.connection_info.get(mock_ws, {}).get("user_id") == 123

    @pytest.mark.asyncio
    async def test_disconnect_websocket(self) -> None:
        """Test WebSocket disconnection"""
        mock_ws = MockWebSocket()

        await self.manager.connect(mock_ws, "leaderboard", user_id=123)
        self.manager.disconnect(mock_ws)

        assert mock_ws not in self.manager.connection_info
        assert "leaderboard" not in self.manager.connections  # Should be cleaned up

    @pytest.mark.asyncio
    async def test_send_to_connection_type(self) -> None:
        """Test sending message to specific connection type"""
        mock_ws1 = MockWebSocket()
        mock_ws2 = MockWebSocket()

        await self.manager.connect(mock_ws1, "leaderboard", user_id=123)
        await self.manager.connect(mock_ws2, "leaderboard", user_id=456)

        message = {"type": "test", "data": "hello"}
        await self.manager.send_to_connection_type("leaderboard", message)

        expected_message = json.dumps(message)
        assert expected_message in mock_ws1.messages_sent
        assert expected_message in mock_ws2.messages_sent

    @pytest.mark.asyncio
    async def test_send_to_user(self) -> None:
        """Test sending message to specific user"""
        mock_ws1 = MockWebSocket()
        mock_ws2 = MockWebSocket()

        await self.manager.connect(mock_ws1, "leaderboard", user_id=123)
        await self.manager.connect(mock_ws2, "leaderboard", user_id=456)

        message = {"type": "test", "data": "hello user 123"}
        await self.manager.send_to_user(123, message)

        expected_message = json.dumps(message)
        assert expected_message in mock_ws1.messages_sent
        assert expected_message not in mock_ws2.messages_sent

    @pytest.mark.asyncio
    async def test_cleanup_disconnected_connections(self) -> None:
        """Test automatic cleanup of disconnected connections"""
        mock_ws = MockWebSocket()

        await self.manager.connect(mock_ws, "leaderboard", user_id=123)
        mock_ws.close()  # Simulate disconnection

        message = {"type": "test", "data": "hello"}
        await self.manager.send_to_connection_type("leaderboard", message)

        # Connection should be cleaned up
        assert mock_ws not in self.manager.connection_info
        assert "leaderboard" not in self.manager.connections

    def test_get_connection_count(self) -> None:
        """Test getting connection count"""
        assert self.manager.get_connection_count() == 0
        assert self.manager.get_connection_count("leaderboard") == 0


class TestLeaderboardNotificationService:
    """Tests for leaderboard notification service"""

    @pytest.mark.asyncio
    async def test_notify_leaderboard_update(
        self, async_session: AsyncSession, test_users: List[User], game_sessions: List[GameSession]
    ) -> None:
        """Test leaderboard update notification"""
        repository = GameSessionRepository(async_session)
        service = LeaderboardNotificationService(repository)

        # Mock websocket manager
        with patch(
            "app.infrastructure.services.leaderboard_notification_service.websocket_manager"
        ) as mock_manager:
            mock_manager.send_to_connection_type = AsyncMock()

            await service.notify_leaderboard_update(test_users[0].id)

            # Verify message was sent
            mock_manager.send_to_connection_type.assert_called_once()
            call_args = mock_manager.send_to_connection_type.call_args
            assert call_args[0][0] == "leaderboard"  # connection type

            message = call_args[0][1]  # message
            assert message["type"] == "leaderboard_update"
            assert "data" in message
            assert "leaderboard" in message["data"]
            assert message["triggered_by_user"] == test_users[0].id

    @pytest.mark.asyncio
    async def test_notify_new_high_score(self, async_session: AsyncSession) -> None:
        """Test new high score notification"""
        repository = GameSessionRepository(async_session)
        service = LeaderboardNotificationService(repository)

        with patch(
            "app.infrastructure.services.leaderboard_notification_service.websocket_manager"
        ) as mock_manager:
            mock_manager.send_to_connection_type = AsyncMock()

            await service.notify_new_high_score(123, "test_user", 25)

            mock_manager.send_to_connection_type.assert_called_once()
            call_args = mock_manager.send_to_connection_type.call_args

            message = call_args[0][1]
            assert message["type"] == "new_high_score"
            assert message["data"]["user_id"] == 123
            assert message["data"]["username"] == "test_user"
            assert message["data"]["deviation_ms"] == 25

    @pytest.mark.asyncio
    async def test_notify_rank_change(self, async_session: AsyncSession) -> None:
        """Test rank change notification"""
        repository = GameSessionRepository(async_session)
        service = LeaderboardNotificationService(repository)

        with patch(
            "app.infrastructure.services.leaderboard_notification_service.websocket_manager"
        ) as mock_manager:
            mock_manager.send_to_user = AsyncMock()

            await service.notify_user_rank_change(123, new_rank=1, old_rank=3)

            mock_manager.send_to_user.assert_called_once()
            call_args = mock_manager.send_to_user.call_args

            assert call_args[0][0] == 123  # user_id
            message = call_args[0][1]
            assert message["type"] == "rank_change"
            assert message["data"]["user_id"] == 123
            assert message["data"]["new_rank"] == 1
            assert message["data"]["old_rank"] == 3
            assert message["data"]["improved"] is True

    @pytest.mark.asyncio
    async def test_send_connection_status(
        self, async_session: AsyncSession, test_users: List[User], game_sessions: List[GameSession]
    ) -> None:
        """Test sending connection status"""
        repository = GameSessionRepository(async_session)
        service = LeaderboardNotificationService(repository)
        mock_ws = MockWebSocket()

        await service.send_connection_status(mock_ws)

        assert len(mock_ws.messages_sent) == 1
        message_data = mock_ws.messages_sent[0].replace("'", '"')

        # Should contain connection established message
        assert "connection_established" in message_data


class TestWebSocketEndpoints:
    """Tests for WebSocket API endpoints"""

    @pytest.mark.asyncio
    async def test_websocket_status_endpoint(self) -> None:
        """Test WebSocket status endpoint"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/ws/connections/status")

            assert response.status_code == 200
            data = response.json()
            assert "leaderboard_connections" in data
            assert "total_connections" in data
            assert "connection_types" in data

    @pytest.mark.asyncio
    async def test_websocket_ping_pong(self, async_session: AsyncSession) -> None:
        """Test WebSocket ping/pong functionality"""
        from app.infrastructure.repositories.game_session_repository import GameSessionRepository
        from app.infrastructure.services.leaderboard_notification_service import (
            LeaderboardNotificationService,
        )
        from app.presentation.api.websockets import handle_client_message

        mock_ws = MockWebSocket()
        repository = GameSessionRepository(async_session)
        service = LeaderboardNotificationService(repository)

        ping_message = {"type": "ping"}

        await handle_client_message(mock_ws, ping_message, service, user_id=123)

        assert len(mock_ws.messages_sent) == 1
        response = json.loads(mock_ws.messages_sent[0])
        assert response["type"] == "pong"
        assert response["data"]["message"] == "Connection alive"

    @pytest.mark.asyncio
    async def test_websocket_request_leaderboard(
        self, async_session: AsyncSession, test_users: List[User], game_sessions: List[GameSession]
    ) -> None:
        """Test WebSocket leaderboard request"""
        from app.infrastructure.repositories.game_session_repository import GameSessionRepository
        from app.infrastructure.services.leaderboard_notification_service import (
            LeaderboardNotificationService,
        )
        from app.presentation.api.websockets import handle_client_message

        mock_ws = MockWebSocket()
        repository = GameSessionRepository(async_session)
        service = LeaderboardNotificationService(repository)

        request_message = {"type": "request_leaderboard"}

        await handle_client_message(mock_ws, request_message, service, user_id=123)

        # Should send connection status with current leaderboard
        assert len(mock_ws.messages_sent) == 1
        message_content = mock_ws.messages_sent[0]
        assert "connection_established" in message_content

    @pytest.mark.asyncio
    async def test_websocket_subscribe_user_updates(self, async_session: AsyncSession) -> None:
        """Test WebSocket user subscription"""
        from app.infrastructure.repositories.game_session_repository import GameSessionRepository
        from app.infrastructure.services.leaderboard_notification_service import (
            LeaderboardNotificationService,
        )
        from app.infrastructure.services.websocket_manager import websocket_manager
        from app.presentation.api.websockets import handle_client_message

        mock_ws = MockWebSocket()
        repository = GameSessionRepository(async_session)
        service = LeaderboardNotificationService(repository)

        # Add websocket to manager first
        await websocket_manager.connect(mock_ws, "leaderboard", user_id=123)

        subscribe_message = {"type": "subscribe_user_updates", "data": {"user_id": 456}}

        await handle_client_message(mock_ws, subscribe_message, service, user_id=123)

        # Should confirm subscription
        assert len(mock_ws.messages_sent) == 1
        response = json.loads(mock_ws.messages_sent[0])
        assert response["type"] == "subscription_confirmed"
        assert response["data"]["user_id"] == 456

        # Cleanup
        websocket_manager.disconnect(mock_ws)

    @pytest.mark.asyncio
    async def test_websocket_unknown_message_type(self, async_session: AsyncSession) -> None:
        """Test WebSocket unknown message handling"""
        from app.infrastructure.repositories.game_session_repository import GameSessionRepository
        from app.infrastructure.services.leaderboard_notification_service import (
            LeaderboardNotificationService,
        )
        from app.presentation.api.websockets import handle_client_message

        mock_ws = MockWebSocket()
        repository = GameSessionRepository(async_session)
        service = LeaderboardNotificationService(repository)

        unknown_message = {"type": "unknown_type"}

        await handle_client_message(mock_ws, unknown_message, service, user_id=123)

        assert len(mock_ws.messages_sent) == 1
        response = json.loads(mock_ws.messages_sent[0])
        assert response["type"] == "error"
        assert "Unknown message type" in response["data"]["message"]

    @pytest.mark.asyncio
    async def test_websocket_invalid_json_handling(self, async_session: AsyncSession) -> None:
        """Test WebSocket invalid JSON handling"""
        # This would be tested in the actual WebSocket endpoint
        # We're testing the error handling logic here
        from app.infrastructure.repositories.game_session_repository import GameSessionRepository
        from app.infrastructure.services.leaderboard_notification_service import (
            LeaderboardNotificationService,
        )
        from app.presentation.api.websockets import handle_client_message

        mock_ws = MockWebSocket()
        repository = GameSessionRepository(async_session)
        service = LeaderboardNotificationService(repository)

        # Test with malformed message (missing required fields)
        malformed_message: Dict[str, Any] = {}

        await handle_client_message(mock_ws, malformed_message, service, user_id=123)

        assert len(mock_ws.messages_sent) == 1
        response = json.loads(mock_ws.messages_sent[0])
        assert response["type"] == "error"


class TestWebSocketIntegrationWithGameFlow:
    """Integration tests for WebSocket notifications with game completion"""

    @pytest.mark.asyncio
    async def test_game_completion_triggers_websocket_notification(
        self, async_session: AsyncSession
    ) -> None:
        """Test that completing a game triggers WebSocket notification"""
        # Create test user
        user = User(
            username="test_gamer",
            email="test@gamer.com",
            password_hash=get_password_hash("testpass123"),
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        with patch(
            "app.presentation.api.games.LeaderboardNotificationService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service

            # Test game completion through API
            async with AsyncClient(app=app, base_url="http://test") as client:
                # Create auth headers
                token = create_token_for_user(user.id, user.username)
                headers = {"Authorization": f"Bearer {token}"}

                # Start game
                start_response = await client.post("/games/start", headers=headers)
                assert start_response.status_code == 201
                session_id = start_response.json()["session_id"]

                # Stop game
                stop_response = await client.post(f"/games/{session_id}/stop", headers=headers)
                assert stop_response.status_code == 200

                # Verify notification service was called
                mock_service.notify_leaderboard_update.assert_called_once_with(user.id)

    @pytest.mark.asyncio
    async def test_high_score_detection_and_notification(self, async_session: AsyncSession) -> None:
        """Test detection and notification of new high scores"""
        # Create test user
        user = User(
            username="champion",
            email="champion@test.com",
            password_hash=get_password_hash("testpass123"),
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        # Create an existing session with higher deviation
        existing_session = GameSession(
            user_id=user.id,
            start_time=datetime.utcnow(),
            stop_time=datetime.utcnow(),
            duration_ms=10100,
            deviation_ms=100,
            status="completed",
        )
        async_session.add(existing_session)
        await async_session.commit()

        with patch(
            "app.presentation.api.games.LeaderboardNotificationService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service

            # Mock get_leaderboard to return the existing session as current best
            mock_service.notify_leaderboard_update = AsyncMock()
            mock_service.notify_new_high_score = AsyncMock()

            # Test game completion through API
            async with AsyncClient(app=app, base_url="http://test") as client:
                token = create_token_for_user(user.id, user.username)
                headers = {"Authorization": f"Bearer {token}"}

                start_response = await client.post("/games/start", headers=headers)
                session_id = start_response.json()["session_id"]

                stop_response = await client.post(f"/games/{session_id}/stop", headers=headers)
                assert stop_response.status_code == 200

                # Verify leaderboard update was called
                mock_service.notify_leaderboard_update.assert_called_once()


@pytest.mark.asyncio
async def test_websocket_performance_with_multiple_connections() -> None:
    """Test WebSocket performance with multiple concurrent connections"""
    manager = WebSocketManager()

    # Create multiple mock connections
    connections = [MockWebSocket() for _ in range(10)]

    # Connect all websockets
    for i, ws in enumerate(connections):
        await manager.connect(ws, "leaderboard", user_id=i)

    # Send message to all connections
    message = {"type": "test", "data": "performance test"}
    await manager.send_to_connection_type("leaderboard", message)

    # Verify all connections received the message
    expected_message = json.dumps(message)
    for ws in connections:
        assert expected_message in ws.messages_sent

    # Test connection count
    assert manager.get_connection_count("leaderboard") == 10
    assert manager.get_connection_count() == 10

    # Disconnect all
    for ws in connections:
        manager.disconnect(ws)

    assert manager.get_connection_count() == 0


@pytest.mark.asyncio
async def test_websocket_error_resilience() -> None:
    """Test WebSocket error handling and resilience"""
    manager = WebSocketManager()

    # Create one good connection and one that will fail
    good_ws = MockWebSocket()
    failing_ws = MockWebSocket()
    failing_ws.close()  # Simulate failed connection

    await manager.connect(good_ws, "leaderboard", user_id=1)
    await manager.connect(failing_ws, "leaderboard", user_id=2)

    # Send message - should not fail due to one bad connection
    message = {"type": "test", "data": "resilience test"}
    await manager.send_to_connection_type("leaderboard", message)

    # Good connection should receive message, failed connection should be cleaned up
    expected_message = json.dumps(message)
    assert expected_message in good_ws.messages_sent
    assert failing_ws not in manager.connection_info

    # Only one connection should remain
    assert manager.get_connection_count("leaderboard") == 1
