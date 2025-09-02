"""Time It Right - FastAPI Game Application

A timer-based game where users try to stop a timer at exactly 10 seconds.
"""

import logging

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.infrastructure.database.connection import create_tables
from app.presentation.api.analytics import router as analytics_router

# Import routers
from app.presentation.api.auth import router as auth_router
from app.presentation.api.games import router as games_router
from app.presentation.api.leaderboard import router as leaderboard_router
from app.presentation.api.websockets import router as websockets_router


def create_application() -> FastAPI:
    """Create and configure FastAPI application"""

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),  # Console output
        ],
    )

    # Set specific loggers
    logging.getLogger("app").setLevel(logging.INFO)
    logging.getLogger("uvicorn").setLevel(logging.INFO)

    app = FastAPI(
        title=settings.app_name,
        description="Timer-based game where users try to stop timer at exactly 10 seconds",
        version=settings.version,
        debug=settings.debug,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
    app.include_router(games_router, prefix="/games", tags=["Game Sessions"])
    app.include_router(leaderboard_router, prefix="/leaderboard", tags=["Leaderboard"])
    app.include_router(analytics_router, prefix="/analytics", tags=["User Analytics"])
    app.include_router(websockets_router, prefix="/ws", tags=["WebSocket Connections"])

    return app


# Create FastAPI app
app = create_application()


@app.on_event("startup")
async def startup_event() -> None:
    """Application startup event"""
    create_tables()


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint"""
    return {
        "message": "Welcome to Time It Right!",
        "description": "Try to stop the timer at exactly 10 seconds",
        "version": settings.version,
        "docs": "/docs",
    }


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint"""
    from datetime import datetime

    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.version,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


def start() -> None:
    """Start the server"""
    uvicorn.run(
        "app.main:app",  # Import string para habilitar reload
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info",
    )
