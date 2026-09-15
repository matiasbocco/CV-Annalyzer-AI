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

    # Analysis limits
    max_cvs_per_analysis: int = 30

    # Deployment / production settings.
    # frontend_url: origin(s) allowed by CORS and used to build links sent to
    # users (e.g. the password-reset email). Comma-separate multiple origins.
    frontend_url: str = "http://localhost:5173"
    # cookie_secure: must be True in production (HTTPS) so the refresh_token
    # cookie is only ever sent over TLS. Keep False for local HTTP dev.
    cookie_secure: bool = False
    # chroma_db_path: where the ChromaDB persistent client stores its files.
    # Point this at a mounted volume in production so the CV bank survives
    # redeploys/restarts.
    chroma_db_path: str = "./chroma_db"

    # Internal service-to-service vector API (ver vector_service.py).
    # Se setea SOLO en producción, y SOLO en el servicio del worker de
    # Celery, apuntando a la URL de red privada de Railway del backend.
    # Cuando está seteado, TODAS las operaciones de ChromaDB del worker se
    # reenvían al backend por HTTP en vez de tocar un Chroma local — así
    # queda un único store autoritativo (el del backend) en vez de dos
    # volúmenes que pueden desincronizarse en silencio.
    internal_vector_api_url: str = ""
    # Secreto compartido que validan los endpoints /internal/vector/* y que
    # envía el worker cuando internal_vector_api_url está seteado. Debe ser
    # IDÉNTICO en backend y worker en producción. El default de acá abajo
    # solo aplica a desarrollo local (donde internal_vector_api_url queda
    # vacío y este secreto nunca se usa).
    internal_api_secret: str = "dev-internal-secret-not-for-production"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_url.split(",") if origin.strip()]

    @property
    def cookie_samesite(self) -> str:
        # SameSite=None requires Secure=True, and is only needed when frontend and
        # backend live on different registrable domains (e.g. two Railway
        # subdomains). Locally both run on localhost, so "lax" is correct.
        return "none" if self.cookie_secure else "lax"


settings = Settings()
