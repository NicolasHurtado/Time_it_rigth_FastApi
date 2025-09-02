"""Duration value object"""

from dataclasses import dataclass
from typing import Union


@dataclass(frozen=True)
class Duration:
    """Duration value object for time measurements"""

    milliseconds: int

    def __post_init__(self) -> None:
        """Validate duration"""
        if self.milliseconds < 0:
            raise ValueError("Duration cannot be negative")

    @classmethod
    def from_seconds(cls, seconds: Union[int, float]) -> "Duration":
        """Create duration from seconds"""
        return cls(int(seconds * 1000))

    @property
    def seconds(self) -> float:
        """Get duration in seconds"""
        return self.milliseconds / 1000.0

    @property
    def minutes(self) -> float:
        """Get duration in minutes"""
        return self.seconds / 60.0

    def __str__(self) -> str:
        """String representation"""
        return f"{self.seconds:.3f}s"

    def __add__(self, other: "Duration") -> "Duration":
        """Add two durations"""
        return Duration(self.milliseconds + other.milliseconds)

    def __sub__(self, other: "Duration") -> "Duration":
        """Subtract two durations"""
        result_ms = self.milliseconds - other.milliseconds
        if result_ms < 0:
            raise ValueError("Cannot subtract larger duration from smaller one")
        return Duration(result_ms)
