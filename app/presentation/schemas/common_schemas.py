"""Common schemas for API responses"""

from typing import Any, Optional

from pydantic import BaseModel


class SuccessResponse(BaseModel):
    """Standard success response schema"""

    success: bool = True
    message: str
    data: Optional[Any] = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Operation completed successfully",
                "data": None,
            }
        }


class ErrorResponse(BaseModel):
    """Standard error response schema"""

    success: bool = False
    message: str
    error_code: Optional[str] = None
    details: Optional[Any] = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "message": "An error occurred",
                "error_code": "VALIDATION_ERROR",
                "details": None,
            }
        }


class HealthCheckResponse(BaseModel):
    """Health check response schema"""

    status: str = "healthy"
    app: str
    version: str
    timestamp: str

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "app": "Time It Right",
                "version": "0.1.0",
                "timestamp": "2024-01-01T12:00:00Z",
            }
        }
