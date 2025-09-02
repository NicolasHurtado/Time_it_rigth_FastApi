"""User domain entity"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class UserEntity:
    """User domain entity"""

    id: Optional[int]
    username: str
    email: str
    password_hash: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        """Post initialization processing"""
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()

    def is_valid_username(self) -> bool:
        """Validate username format"""
        import re

        # Allow alphanumeric characters and underscores
        pattern = r"^[a-zA-Z0-9_]+$"
        return (
            len(self.username) >= 3
            and len(self.username) <= 50
            and re.match(pattern, self.username) is not None
        )

    def is_valid_email(self) -> bool:
        """Basic email validation"""
        return "@" in self.email and "." in self.email.split("@")[1]
