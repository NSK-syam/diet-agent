"""Configuration management for Diet Agent."""

from pydantic_settings import BaseSettings
from typing import Literal
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Supabase
    supabase_url: str
    supabase_key: str

    # Telegram
    telegram_bot_token: str

    # AI Provider
    ai_provider: Literal["ollama", "groq", "gemini", "rule_based"] = "ollama"

    # Ollama
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # Groq
    groq_api_key: str = ""

    # Gemini
    gemini_api_key: str = ""

    # Notification Settings
    morning_plan_time: str = "07:00"
    evening_summary_time: str = "20:00"
    enable_water_reminders: bool = False
    water_reminder_interval: int = 2  # hours

    # Timezone
    timezone: str = "America/New_York"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
