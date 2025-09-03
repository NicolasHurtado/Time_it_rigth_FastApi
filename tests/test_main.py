"""Basic async tests for the main application"""

import pytest
from httpx import AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_root_endpoint() -> None:
    """Test root endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Welcome to Time It Right!" in data["message"]
        assert data["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_health_check() -> None:
    """Test health check endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["app"] == "Time It Right"  # From updated .env
        assert data["version"] == "0.1.0"
        assert "timestamp" in data


@pytest.mark.asyncio
async def test_openapi_docs() -> None:
    """Test that OpenAPI docs are accessible"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/docs")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_openapi_json() -> None:
    """Test that OpenAPI JSON is accessible"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert data["info"]["title"] == "Time It Right"
