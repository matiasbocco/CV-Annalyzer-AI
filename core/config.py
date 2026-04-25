from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    openai_api_key: str
    openai_model: str = "gpt-4o-mini"

    database_url: str = (
        "mysql+aiomysql://cvuser:cvpass@localhost:3306/cv_analyzer"
    )


settings = Settings()
