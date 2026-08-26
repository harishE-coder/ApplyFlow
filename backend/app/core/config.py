"""
Application configuration using pydantic-settings.
Loads from .env file and environment variables.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Apply Flow application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "applyflow"
    db_user: str = "applyflow_user"
    db_password: str = "strong_password"
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

    @property
    def database_url(self) -> str:
        """Async connection URL."""
        if self.database_url_override:
            return self.database_url_override
        if self.use_sqlite:
            return "sqlite+aiosqlite:///./applyflow.db"
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def database_url_sync(self) -> str:
        """Sync URL."""
        if self.use_sqlite:
            return "sqlite:///./applyflow.db"
        return (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = Settings()

