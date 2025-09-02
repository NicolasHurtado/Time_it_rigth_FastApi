"""Authentication API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases.auth_use_cases import LoginUserUseCase, RegisterUserUseCase
from app.core.dependencies import get_current_active_user
from app.infrastructure.database.connection import get_async_db
from app.infrastructure.database.models import User
from app.infrastructure.repositories.user_repository import UserRepository
from app.presentation.schemas.auth_schemas import (
    LoginResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.presentation.schemas.common_schemas import SuccessResponse

router = APIRouter()


@router.post(
    "/register",
    response_model=SuccessResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Create a new user account with username, email and password",
)
async def register(
    user_data: UserRegisterRequest, db: AsyncSession = Depends(get_async_db)
) -> SuccessResponse:
    """Register a new user"""
    try:
        user_repository = UserRepository(db)
        register_use_case = RegisterUserUseCase(user_repository)

        user = await register_use_case.execute(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
        )

        return SuccessResponse(
            message="User registered successfully",
            data={"user_id": user.id, "username": user.username, "email": user.email},
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid registration data: {e}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during registration: {e}",
        )


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="User login",
    description="Authenticate user and receive JWT access token",
)
async def login(
    credentials: UserLoginRequest, db: AsyncSession = Depends(get_async_db)
) -> LoginResponse:
    """Authenticate user and return access token"""
    try:
        user_repository = UserRepository(db)
        login_use_case = LoginUserUseCase(user_repository)

        result = await login_use_case.execute(
            username=credentials.username, password=credentials.password
        )

        return LoginResponse(**result)

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login",
        )


@router.get(
    "/profile",
    response_model=UserResponse,
    summary="Get user profile",
    description="Get current user's profile information",
)
async def get_profile(current_user: User = Depends(get_current_active_user)) -> UserResponse:
    """Get current user's profile"""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
    )
