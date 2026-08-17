from pydantic_settings import SettingsConfigDict

from packages.db.session import Settings as DbSettings


class Settings(DbSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    redis_url: str = "redis://localhost:6379/0"
    llm_provider: str = "fake"
    headless: bool = True
    dashboard_api_base_url: str = "http://localhost:8000"
    cors_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
