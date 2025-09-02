"""Authentication schemas for request/response validation"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserRegisterRequest(BaseModel):
    """Schema for user registration request"""

    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Username (3-50 characters, alphanumeric and underscores)",
    )
    email: EmailStr = Field(..., description="Valid email address")
    password: str = Field(
        ..., min_length=6, max_length=100, description="Password (6-100 characters)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "username": "player123",
                "email": "player@example.com",
                "password": "securepassword",
            }
        }


class UserLoginRequest(BaseModel):
    """Schema for user login request"""

    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")

    class Config:
        json_schema_extra = {"example": {"username": "player123", "password": "securepassword"}}


class UserResponse(BaseModel):
    """Schema for user data in responses"""

    id: int
    username: str
    email: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    """Schema for login response"""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "user": {
                    "id": 1,
                    "username": "player123",
                    "email": "player@example.com",
                    "created_at": "2024-01-01T00:00:00",
                    "updated_at": "2024-01-01T00:00:00",
                },
            }
        }


class TokenData(BaseModel):
    """Schema for token payload data"""

    username: Optional[str] = None
    user_id: Optional[int] = None
