"""Async tests for authentication endpoints using httpx.AsyncClient"""

import random
from datetime import datetime, timedelta
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_token_for_user, get_password_hash
from app.infrastructure.database.connection import Base, get_async_db
from app.infrastructure.database.models import GameSession, User
from app.main import app


# Custom AsyncClient with test session
class TestAsyncClient(AsyncClient):
    """AsyncClient with test_session attribute for testing"""

    test_session: AsyncSession


# Helper functions for testing authentication


def get_auth_headers(user_id: int, username: str) -> dict[str, str]:
    """Get authentication headers for testing"""
    token = create_token_for_user(user_id, username)
    return {"Authorization": f"Bearer {token}"}


# Create async test database
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
async def async_client() -> AsyncGenerator[TestAsyncClient, None]:
    """Create async test client"""
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingAsyncSessionLocal() as session:
        async with TestAsyncClient(app=app, base_url="http://test") as client:
            # Make session available to tests
            client.test_session = session
            yield client

    # Drop tables after test
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_user_registration_async(async_client: TestAsyncClient) -> None:
    """Test user registration with async client"""
    user_data = {"username": "testuser", "email": "test@example.com", "password": "testpass123"}

    response = await async_client.post("/auth/register", json=user_data)

    assert response.status_code == 201
    data = response.json()
    assert data["message"] == "User registered successfully"
    assert data["data"]["user_id"] is not None


@pytest.mark.asyncio
async def test_user_login_async(async_client: TestAsyncClient) -> None:
    """Test user login with async client"""
    # First register a user
    user_data = {"username": "testuser", "email": "test@example.com", "password": "testpass123"}

    register_response = await async_client.post("/auth/register", json=user_data)
    assert register_response.status_code == 201

    # Then login
    login_data = {"username": "testuser", "password": "testpass123"}

    response = await async_client.post("/auth/login", json=login_data)

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "testuser"
    assert data["user"]["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_user_profile_async(async_client: TestAsyncClient) -> None:
    """Test getting user profile with async client"""
    # Register and login to get token
    user_data = {"username": "testuser", "email": "test@example.com", "password": "testpass123"}

    await async_client.post("/auth/register", json=user_data)

    login_response = await async_client.post(
        "/auth/login", json={"username": "testuser", "password": "testpass123"}
    )

    token = login_response.json()["access_token"]

    # Get profile
    response = await async_client.get("/auth/profile", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_game_flow_async(async_client: TestAsyncClient) -> None:
    """Test complete game flow with async client"""
    # Register and login
    user_data = {"username": "gamer123", "email": "gamer@example.com", "password": "gamepass123"}

    await async_client.post("/auth/register", json=user_data)

    login_response = await async_client.post(
        "/auth/login", json={"username": "gamer123", "password": "gamepass123"}
    )

    print("login_response", login_response.json())

    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Start game
    start_response = await async_client.post("/games/start", headers=headers)
    print("start_response", start_response.json())
    assert start_response.status_code == 201

    start_data = start_response.json()
    session_id = start_data["session_id"]
    assert start_data["target_time_ms"] == 10000

    # Stop game
    stop_response = await async_client.post(f"/games/{session_id}/stop", headers=headers)
    print("stop_response", stop_response.json())
    assert stop_response.status_code == 200

    stop_data = stop_response.json()
    assert stop_data["session_id"] == session_id
    assert "duration_ms" in stop_data
    assert "deviation_ms" in stop_data
    assert "accuracy_score" in stop_data


@pytest.mark.asyncio
async def test_leaderboard_with_realistic_data(async_client: TestAsyncClient) -> None:
    """Test leaderboard endpoint with realistic game data"""
    session = async_client.test_session

    # Create realistic game scenario with multiple users and sessions
    print("\n🎮 Creating realistic game data...")

    # Create users with different skill levels using direct model creation
    pro_gamer = User(
        username="pro_gamer_mike",
        email="mike@progamer.com",
        password_hash=get_password_hash("testpass123"),
    )
    casual_player = User(
        username="weekend_warrior",
        email="casual@gamer.com",
        password_hash=get_password_hash("testpass123"),
    )
    newbie = User(
        username="just_started",
        email="newbie@beginner.com",
        password_hash=get_password_hash("testpass123"),
    )
    veteran = User(
        username="old_school_timer",
        email="veteran@classic.com",
        password_hash=get_password_hash("testpass123"),
    )

    session.add_all([pro_gamer, casual_player, newbie, veteran])
    await session.commit()
    await session.refresh(pro_gamer)
    await session.refresh(casual_player)
    await session.refresh(newbie)
    await session.refresh(veteran)

    # Create game sessions with realistic performance patterns
    print("🎯 Creating game sessions...")

    # Pro gamer: Consistently accurate (deviation 50-200ms)
    pro_sessions = []
    for i in range(5):
        duration = random.randint(9900, 10100)  # Very close to 10 seconds
        session_obj = GameSession(
            user_id=pro_gamer.id,
            start_time=datetime.utcnow() - timedelta(minutes=5),
            stop_time=datetime.utcnow(),
            duration_ms=duration,
            deviation_ms=abs(duration - 10000),
            status="completed",
        )
        pro_sessions.append(session_obj)

    # Casual player: Good but inconsistent (deviation 100-500ms)
    casual_sessions = []
    for i in range(3):
        duration = random.randint(9600, 10400)  # Pretty good
        session_obj = GameSession(
            user_id=casual_player.id,
            start_time=datetime.utcnow() - timedelta(minutes=5),
            stop_time=datetime.utcnow(),
            duration_ms=duration,
            deviation_ms=abs(duration - 10000),
            status="completed",
        )
        casual_sessions.append(session_obj)

    # Newbie: Learning (deviation 500-2000ms)
    newbie_sessions = []
    for i in range(2):
        duration = random.randint(8500, 11500)  # Still learning
        session_obj = GameSession(
            user_id=newbie.id,
            start_time=datetime.utcnow() - timedelta(minutes=5),
            stop_time=datetime.utcnow(),
            duration_ms=duration,
            deviation_ms=abs(duration - 10000),
            status="completed",
        )
        newbie_sessions.append(session_obj)

    # Veteran: Moderate skill (deviation 200-800ms)
    veteran_sessions = []
    for i in range(4):
        duration = random.randint(9300, 10700)  # Decent but not perfect
        session_obj = GameSession(
            user_id=veteran.id,
            start_time=datetime.utcnow() - timedelta(minutes=5),
            stop_time=datetime.utcnow(),
            duration_ms=duration,
            deviation_ms=abs(duration - 10000),
            status="completed",
        )
        veteran_sessions.append(session_obj)

    all_sessions = pro_sessions + casual_sessions + newbie_sessions + veteran_sessions
    session.add_all(all_sessions)
    await session.commit()

    print(f"✅ Created {len(all_sessions)} game sessions for 4 users")

    # Test leaderboard endpoint
    response = await async_client.get("/leaderboard")
    print("responseeeee", response.json())

    assert response.status_code == 200
    data = response.json()
    assert "leaderboard" in data

    leaderboard = data["leaderboard"]
    print("\n🏆 Leaderboard Results:")

    # Verify leaderboard structure and data
    assert isinstance(leaderboard, list)
    assert len(leaderboard) == 4  # All 4 users should appear

    # Verify leaderboard is sorted by best average deviation (ascending)
    for i, entry in enumerate(leaderboard):
        print(
            f"  {entry['rank']}. {entry['username']} - "
            f"Avg: {entry['avg_deviation_ms']}ms, Games: {entry['total_games']}"
        )

        assert "rank" in entry
        assert "username" in entry
        assert "avg_deviation_ms" in entry
        assert "total_games" in entry
        assert entry["rank"] == i + 1

        # Pro gamer should be #1 (lowest average deviation)
        if i == 0:
            assert entry["username"] == "pro_gamer_mike"
            assert entry["avg_deviation_ms"] < 200  # Pro accuracy
            assert entry["total_games"] == 5

    # Verify rankings are in correct order (best to worst)
    for i in range(len(leaderboard) - 1):
        current_avg = leaderboard[i]["avg_deviation_ms"]
        next_avg = leaderboard[i + 1]["avg_deviation_ms"]
        assert (
            current_avg <= next_avg
        ), f"Leaderboard not sorted correctly: {current_avg} > {next_avg}"

    print("✅ Leaderboard test passed with realistic data!")
    winner_name = leaderboard[0]["username"]
    winner_avg = leaderboard[0]["avg_deviation_ms"]
    print(f"   Winner: {winner_name} with {winner_avg}ms avg deviation")


@pytest.mark.asyncio
async def test_analytics_with_realistic_data(async_client: TestAsyncClient) -> None:
    """Test analytics endpoint with realistic data"""
    session = async_client.test_session

    # Create users with different skill levels using direct model creation
    pro_gamer = User(
        username="pro_gamer_mike",
        email="mike@progamer.com",
        password_hash=get_password_hash("testpass123"),
    )
    casual_player = User(
        username="weekend_warrior",
        email="casual@gamer.com",
        password_hash=get_password_hash("testpass123"),
    )
    session.add_all([pro_gamer, casual_player])
    await session.commit()
    await session.refresh(pro_gamer)
    await session.refresh(casual_player)

    # Pro gamer: Consistently accurate (deviation 50-200ms)
    pro_sessions = []
    for i in range(5):
        duration = random.randint(9900, 10100)  # Very close to 10 seconds
        session_obj = GameSession(
            user_id=pro_gamer.id,
            start_time=datetime.utcnow() - timedelta(minutes=5),
            stop_time=datetime.utcnow(),
            duration_ms=duration,
            deviation_ms=abs(duration - 10000),
            status="completed",
        )
        pro_sessions.append(session_obj)

    # Casual player: Good but inconsistent (deviation 100-500ms)
    casual_sessions = []
    for i in range(3):
        duration = random.randint(9600, 10400)  # Pretty good
        session_obj = GameSession(
            user_id=casual_player.id,
            start_time=datetime.utcnow() - timedelta(minutes=5),
            stop_time=datetime.utcnow(),
            duration_ms=duration,
            deviation_ms=abs(duration - 10000),
            status="completed",
        )
        casual_sessions.append(session_obj)

    all_sessions = pro_sessions + casual_sessions
    session.add_all(all_sessions)
    await session.commit()

    # Test analytics endpoint with authentication
    headers = get_auth_headers(pro_gamer.id, pro_gamer.username)
    response = await async_client.get(f"/analytics/user/{pro_gamer.id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["username"] == pro_gamer.username
    assert response.json()["total_games"] == len(pro_sessions)

    response = await async_client.get(f"/analytics/user/{casual_player.id}", headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "You can only view your own statistics"
