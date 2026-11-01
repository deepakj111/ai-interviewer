"""Application configuration using Pydantic Settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration settings for AI Interviewer backend."""

    # Project Information
    PROJECT_NAME: str = "ai-interviewer"
    API_V1_STR: str = "/api"
    ENVIRONMENT: str = "development"

    # API Keys & Auth (BYOK - Bring Your Own Key)
    GEMINI_API_KEY: str = ""

    # Gemini Models
    LIVE_MODEL: str = "gemini-2.5-flash-native-audio-preview-09-2025"
    REASONING_MODEL: str = "gemini-2.5-pro"
    EXTRACTOR_MODEL: str = "gemini-2.5-flash"

    # Audio Streaming Configuration
    AUDIO_INPUT_SAMPLE_RATE: int = 16000  # 16kHz PCM
    AUDIO_OUTPUT_SAMPLE_RATE: int = 24000  # 24kHz PCM
    AUDIO_CHANNELS: int = 1  # Mono

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./ai_interviewer.db"

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Provide cached settings instance."""
    return Settings()
