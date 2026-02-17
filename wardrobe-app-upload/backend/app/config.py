from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Wardrobe AI"
    debug: bool = True
    api_prefix: str = "/api"

    jwt_secret: str = Field(default="change-me-in-production", min_length=16)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7

    database_url: str = "sqlite:///./backend/wardrobe.db"

    cors_origins: str = (
        "http://localhost:8000,http://127.0.0.1:8000,"
        "http://localhost,capacitor://localhost,ionic://localhost"
    )

    wechat_app_id: str = ""
    wechat_app_secret: str = ""
    wechat_redirect_uri: str = "http://localhost:8000/api/auth/wechat/callback"

    qq_app_id: str = ""
    qq_app_secret: str = ""
    qq_redirect_uri: str = "http://localhost:8000/api/auth/qq/callback"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
