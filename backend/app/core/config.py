"""
Application configuration using pydantic-settings.
Loads from .env file and environment variables.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Apply Flow application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    # Database
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "applyflow"
    db_user: str = "applyflow_user"
    db_password: str = "strong_password"
    database_url_raw: str | None = Field(default=None, alias="database_url")
    database_url_override: str | None = None
    use_sqlite: bool = False

    # JWT
    jwt_secret_key: str = "applyflow-dev-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # Google Apps Script Web App Storage
    google_apps_script_url: str = ""
    google_drive_root_folder_id: str = ""

    # Groq AI
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"

    # CORS
    frontend_url: str = "http://localhost:5173"

    # Initial Admin Seed
    admin_email: str = "Harishabblu123@gmail.com"
    admin_password: str = "Harish@2007"
    admin_name: str = "Harish Admin"

    @property
    def database_url(self) -> str:
        """Async connection URL for SQLAlchemy asyncpg engine."""
        if self.use_sqlite:
            return "sqlite+aiosqlite:///./applyflow.db"

        raw = self.database_url_override or self.database_url_raw
        if raw:
            raw = raw.strip()
            if raw.startswith("postgres://"):
                raw = "postgresql+asyncpg://" + raw[len("postgres://"):]
            elif raw.startswith("postgresql://") and not raw.startswith("postgresql+asyncpg://"):
                raw = "postgresql+asyncpg://" + raw[len("postgresql://"):]
            # asyncpg expects 'ssl=require' instead of 'sslmode=require'
            raw = raw.replace("sslmode=require", "ssl=require")
            raw = raw.replace("sslmode=prefer", "ssl=prefer")
            raw = raw.replace("sslmode=disable", "ssl=disable")
            return raw

        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def database_url_sync(self) -> str:
        """Sync URL for Alembic and migration scripts."""
        if self.use_sqlite:
            return "sqlite:///./applyflow.db"

        raw = self.database_url_override or self.database_url_raw
        if raw:
            raw = raw.strip()
            if raw.startswith("postgresql+asyncpg://"):
                raw = "postgresql+psycopg2://" + raw[len("postgresql+asyncpg://"):]
            elif raw.startswith("postgres://"):
                raw = "postgresql+psycopg2://" + raw[len("postgres://"):]
            elif raw.startswith("postgresql://") and not raw.startswith("postgresql+psycopg2://"):
                raw = "postgresql+psycopg2://" + raw[len("postgresql://"):]
            # psycopg2 expects 'sslmode=require'
            raw = raw.replace("?ssl=require", "?sslmode=require").replace("&ssl=require", "&sslmode=require")
            return raw

        return (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = Settings()

