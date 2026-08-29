from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    openai_api_key: str
    openai_model: str = "gpt-4o-mini"

    database_url: str = (
        "mysql+aiomysql://cvuser:cvpass@localhost:3306/cv_analyzer"
    )

    # Redis URL for Celery broker and result backend.
    # In Docker, override with redis://redis:6379/0 (service name, not localhost).
    redis_url: str = "redis://localhost:6379/0"

    # Authentication
    secret_key: str
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7


settings = Settings()
