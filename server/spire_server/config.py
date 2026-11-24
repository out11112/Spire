"""Configuration for the standalone Spire server."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables and .env."""

    spire_database_url: str = 'sqlite:///./spire.db'
    linkchat_auth_url: str = 'https://linkchat.online'
    auth_cache_ttl_seconds: float = Field(default=30.0, ge=0.0, le=300.0)
    auth_timeout_seconds: float = Field(default=5.0, ge=1.0, le=30.0)
    spire_host: str = '0.0.0.0'
    spire_port: int = 8100

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / '.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
