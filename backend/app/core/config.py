from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Lemon Brothers Product Intelligence"
    app_env: str = "development"
    database_url: str = (
        "postgresql+psycopg://lemonbrothers:lemonbrothers@postgres:5432/lemonbrothers"
    )
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"

    jwt_secret_key: str = "local-development-secret-change-me"
    jwt_access_token_expire_minutes: int = 60
    seed_admin_username: str = "admin"
    seed_admin_password: str = "admin123"

    llm_provider: str = "openai"
    llm_model: str = "gpt-5-mini"
    openai_api_key: str = Field(default="", repr=False)
    gemini_api_key: str = Field(default="", repr=False)
    anthropic_api_key: str = Field(default="", repr=False)
    llm_timeout_seconds: float = 45.0

    amazon_bestsellers_url: str = (
        "https://www.amazon.com/Best-Sellers-Home-Kitchen/zgbs/home-garden/"
    )
    amazon_max_products: int = Field(default=20, ge=1, le=100)

    def provider_api_key(self) -> str:
        provider = self.llm_provider.strip().lower()
        return {
            "openai": self.openai_api_key,
            "gemini": self.gemini_api_key,
            "anthropic": self.anthropic_api_key,
        }.get(provider, "").strip()

    def resolved_llm_model(self) -> str:
        provider = self.llm_provider.strip().lower()
        model = self.llm_model.strip()
        if provider == "gemini" and not model.lower().startswith("gemini-"):
            return "gemini-3.6-flash"
        if provider == "openai" and model.lower().startswith("gemini-"):
            return "gpt-5-mini"
        return model


@lru_cache
def get_settings() -> Settings:
    return Settings()
