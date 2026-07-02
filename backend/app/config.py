from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://lotto:lotto@localhost:5433/lotto"
    jwt_secret: str = "dev-secret-change-me"
    jwt_expire_minutes: int = 60 * 24 * 7
    # NoDecode disables pydantic-settings' default JSON decoding of the env value,
    # so a plain comma-separated string like "*" or "http://a,http://b" is accepted
    # and split by the validator below (bare "*" is not valid JSON).
    cors_allow_origins: Annotated[list[str], NoDecode] = ["*"]
    ocr_provider: str = "mock"
    media_dir: str = "media"

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def _split_origins(cls, v: object) -> object:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
