"""Game session schemas for request/response validation"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class GameSessionResponse(BaseModel):
    """Schema for game session response"""

    id: int
    user_id: int
    start_time: datetime
    stop_time: Optional[datetime] = None
    duration_ms: Optional[int] = None
    deviation_ms: Optional[int] = None
    status: str
    created_at: datetime
    accuracy_score: Optional[float] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "user_id": 1,
                "start_time": "2024-01-01T12:00:00",
                "stop_time": "2024-01-01T12:00:10.123",
                "duration_ms": 10123,
                "deviation_ms": 123,
                "status": "completed",
                "created_at": "2024-01-01T12:00:00",
                "accuracy_score": 98.77,
            }
        }


class StartGameResponse(BaseModel):
    """Schema for start game response"""

    session_id: int
    start_time: datetime
    message: str = "Game started! Try to stop the timer at exactly 10 seconds."
    target_time_ms: int = 10000

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": 1,
                "start_time": "2024-01-01T12:00:00",
                "message": "Game started! Try to stop the timer at exactly 10 seconds.",
                "target_time_ms": 10000,
            }
        }


class StopGameResponse(BaseModel):
    """Schema for stop game response"""

    session_id: int
    duration_ms: int
    deviation_ms: int
    accuracy_score: float
    grade: str
    message: str

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": 1,
                "duration_ms": 10123,
                "deviation_ms": 123,
                "accuracy_score": 98.77,
                "grade": "A",
                "message": "Excellent timing! You were only 123ms off target.",
            }
        }


class LeaderboardEntry(BaseModel):
    """Schema for leaderboard entry"""

    rank: int
    user_id: int
    username: str
    avg_deviation_ms: float
    best_deviation_ms: int
    total_games: int
    accuracy_percentage: Optional[float] = None

    class Config:
        json_schema_extra = {
            "example": {
                "rank": 1,
                "user_id": 1,
                "username": "player123",
                "avg_deviation_ms": 85.5,
                "best_deviation_ms": 23,
                "total_games": 25,
                "accuracy_percentage": 99.15,
            }
        }


class LeaderboardResponse(BaseModel):
    """Schema for leaderboard response"""

    leaderboard: List[LeaderboardEntry]
    total_entries: int

    class Config:
        json_schema_extra = {
            "example": {
                "leaderboard": [
                    {
                        "rank": 1,
                        "user_id": 1,
                        "username": "player123",
                        "avg_deviation_ms": 85.5,
                        "total_games": 25,
                        "accuracy_percentage": 99.15,
                    }
                ],
                "total_entries": 1,
            }
        }


class UserStatsResponse(BaseModel):
    """Schema for user statistics response"""

    user_id: int
    username: str
    total_games: int
    completed_games: int
    avg_deviation_ms: Optional[float] = None
    best_deviation_ms: Optional[int] = None
    avg_accuracy: Optional[float] = None
    games_history: List[GameSessionResponse]

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "username": "player123",
                "total_games": 10,
                "completed_games": 8,
                "avg_deviation_ms": 156.5,
                "best_deviation_ms": 23,
                "avg_accuracy": 98.44,
                "games_history": [],
            }
        }
