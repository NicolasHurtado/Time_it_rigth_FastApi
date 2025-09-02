"""Game session domain entity"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from app.core.config import settings


class SessionStatus(Enum):
    """Game session status"""

    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"


@dataclass
class GameSessionEntity:
    """Game session domain entity"""

    id: Optional[int]
    user_id: int
    start_time: datetime
    stop_time: Optional[datetime] = None
    duration_ms: Optional[int] = None
    deviation_ms: Optional[int] = None
    status: SessionStatus = SessionStatus.ACTIVE
    created_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        """Post initialization processing"""
        if self.created_at is None:
            self.created_at = datetime.utcnow()

    def complete_session(self, stop_time: datetime) -> None:
        """Complete the game session"""
        if self.status != SessionStatus.ACTIVE:
            raise ValueError("Session is not active")

        self.stop_time = stop_time
        self.duration_ms = int((stop_time - self.start_time).total_seconds() * 1000)
        self.deviation_ms = abs(self.duration_ms - settings.target_time_ms)
        self.status = SessionStatus.COMPLETED

    def expire_session(self) -> None:
        """Mark session as expired"""
        if self.status == SessionStatus.ACTIVE:
            self.status = SessionStatus.EXPIRED

    def is_expired(self) -> bool:
        """Check if session should be expired based on time"""
        if self.status != SessionStatus.ACTIVE:
            return False

        expiry_time = self.start_time + timedelta(minutes=settings.session_expire_minutes)
        return datetime.utcnow() > expiry_time

    def get_accuracy_score(self) -> float:
        """Calculate accuracy score (0-100)"""
        if self.deviation_ms is None:
            return 0.0

        # Perfect score for 0 deviation, decreasing with larger deviations
        max_deviation = settings.target_time_ms  # 10 seconds
        accuracy = max(0, 100 * (1 - (self.deviation_ms / max_deviation)))
        return round(accuracy, 2)

    @property
    def is_completed(self) -> bool:
        """Check if session is completed"""
        return self.status == SessionStatus.COMPLETED

    @property
    def is_active(self) -> bool:
        """Check if session is active"""
        return self.status == SessionStatus.ACTIVE
