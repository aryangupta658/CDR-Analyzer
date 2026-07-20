from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Stores application configuration.

    Values are read from the .env file.
    """

    app_name: str = "CDR Analyzer"

    database_url: str = "sqlite:///./cdr_analyzer.db"

    jwt_secret_key: str = "development-secret-key"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    max_upload_size_mb: int = 25
    storage_directory: Path = Path("storage")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()

# Create storage folders automatically.
settings.storage_directory.mkdir(parents=True, exist_ok=True)

originals_directory = settings.storage_directory / "originals"
originals_directory.mkdir(parents=True, exist_ok=True)