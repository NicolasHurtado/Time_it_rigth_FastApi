"""Application configuration settings"""


from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Database
    database_url: str = Field(default="sqlite:///./time_it_right.db", env="DATABASE_URL")

    # Security
    secret_key: str = Field(default="your-secret-key-here-change-in-production", env="SECRET_KEY")
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")

    # Application
    app_name: str = Field(default="Time It Right", env="APP_NAME")
    debug: bool = Field(default=False, env="DEBUG")
    version: str = Field(default="0.1.0", env="VERSION")

    # Game Settings
    target_time_ms: int = Field(default=10000, env="TARGET_TIME_MS")  # 10 seconds
    session_expire_minutes: int = Field(default=30, env="SESSION_EXPIRE_MINUTES")
    leaderboard_top_count: int = Field(default=10, env="LEADERBOARD_TOP_COUNT")

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
