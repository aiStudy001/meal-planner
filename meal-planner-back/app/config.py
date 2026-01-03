"""
FastAPI 서버 설정 관리

Pydantic Settings를 사용한 환경 변수 관리
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import List


class Settings(BaseSettings):
    """서버 설정"""

    # API Keys
    ANTHROPIC_API_KEY: str | None = None
    TAVILY_API_KEY: str | None = None

    # LLM Settings
    LLM_MODEL: str = "claude-3-5-haiku-latest"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 2000

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    # CORS (환경변수에서 쉼표로 구분된 문자열로 설정)
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://localhost:5174"

    # Mock Mode
    MOCK_MODE: bool = False

    # Price Cache Settings
    PRICE_CACHE_DIR: str = "data/price_cache"
    PRICE_CACHE_DAYS: int = 1

    @field_validator("CORS_ORIGINS", mode="after")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse comma-separated CORS origins into a list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("ANTHROPIC_API_KEY", mode="after")
    @classmethod
    def validate_anthropic_api_key(cls, v, info):
        """CRITICAL: Ensure API key is set when not in mock mode"""
        # info.data에서 MOCK_MODE 가져오기
        mock_mode = info.data.get("MOCK_MODE", False)

        if not mock_mode and not v:
            raise ValueError(
                "ANTHROPIC_API_KEY is required when MOCK_MODE=false. "
                "Please set the API key in your .env file or enable MOCK_MODE=true for testing."
            )

        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # .env에 있는 다른 필드들 무시
    )


# 전역 설정 인스턴스
settings = Settings()
