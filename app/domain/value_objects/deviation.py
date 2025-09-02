"""Deviation value object"""

from dataclasses import dataclass

from app.domain.value_objects.duration import Duration


@dataclass(frozen=True)
class Deviation:
    """Deviation value object for measuring accuracy"""

    milliseconds: int
    target_ms: int = 10000  # 10 seconds default target

    def __post_init__(self) -> None:
        """Validate deviation"""
        if self.milliseconds < 0:
            raise ValueError("Deviation cannot be negative")
        if self.target_ms <= 0:
            raise ValueError("Target must be positive")

    @classmethod
    def from_durations(cls, actual: Duration, target: Duration) -> "Deviation":
        """Create deviation from two durations"""
        deviation_ms = abs(actual.milliseconds - target.milliseconds)
        return cls(deviation_ms, target.milliseconds)

    @property
    def accuracy_percentage(self) -> float:
        """Calculate accuracy as percentage (0-100)"""
        if self.milliseconds == 0:
            return 100.0

        # Perfect score for 0 deviation, decreasing with larger deviations
        accuracy = max(0, 100 * (1 - (self.milliseconds / self.target_ms)))
        return round(accuracy, 2)

    @property
    def seconds(self) -> float:
        """Get deviation in seconds"""
        return self.milliseconds / 1000.0

    def is_perfect(self) -> bool:
        """Check if deviation is zero (perfect timing)"""
        return self.milliseconds == 0

    def is_excellent(self) -> bool:
        """Check if deviation is less than 100ms (excellent timing)"""
        return self.milliseconds < 100

    def is_good(self) -> bool:
        """Check if deviation is less than 500ms (good timing)"""
        return self.milliseconds < 500

    def get_grade(self) -> str:
        """Get letter grade based on deviation"""
        if self.is_perfect():
            return "A+"
        elif self.is_excellent():
            return "A"
        elif self.is_good():
            return "B"
        elif self.milliseconds < 1000:
            return "C"
        elif self.milliseconds < 2000:
            return "D"
        else:
            return "F"

    def __str__(self) -> str:
        """String representation"""
        return f"{self.seconds:.3f}s deviation ({self.accuracy_percentage:.1f}%)"
