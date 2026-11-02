"""Centralized environment-backed PyBI settings."""

from typing import Optional

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings shared by application modules."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    data_dir: str = Field(default="pybi_data", validation_alias="DATA_DIR")
    exports_dir: str = Field(
        default="pybi_data/exports",
        validation_alias="EXPORTS_DIR",
    )
    jwt_secret: Optional[str] = Field(default=None, validation_alias="PYBI_JWT_SECRET")
    environment: str = Field(default="development", validation_alias="PYBI_ENV")
    duckdb_threads: Optional[int] = Field(
        default=None,
        validation_alias="DUCKDB_THREADS",
    )
    duckdb_max_memory: Optional[str] = Field(
        default=None,
        validation_alias="DUCKDB_MAX_MEMORY",
    )
    database_url: Optional[str] = Field(default=None, validation_alias="DATABASE_URL")
    redis_url: Optional[str] = Field(default=None, validation_alias="REDIS_URL")

    @model_validator(mode="after")
    def require_production_jwt_secret(self) -> "Settings":
        if self.environment.lower() == "production" and (
            not self.jwt_secret or len(self.jwt_secret) < 32
        ):
            raise ValueError("PYBI_JWT_SECRET must contain at least 32 characters in production")
        return self


def get_settings() -> Settings:
    """Load runtime settings from the environment and local dotenv file."""
    return Settings()
