import os
from functools import lru_cache
from pathlib import Path
from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import AliasChoices, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_ROOT / (".env.production" if os.getenv("APP_ENV") == "production" else ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore", hide_input_in_errors=True
    )
    APP_ENV: Literal["development", "production"] = "development"
    PROJECT_NAME: str = "StudyFlow"
    DATABASE_URL: SecretStr
    ALLOWED_ORIGINS: list[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        validation_alias=AliasChoices("ALLOWED_ORIGINS", "CORS_ORIGINS"),
    )
    ALLOWED_METHODS: list[str] = ["GET", "POST", "PATCH", "DELETE", "OPTIONS"]
    ALLOWED_HEADERS: list[str] = ["Content-Type", "X-Request-ID"]
    TRUSTED_HOSTS: list[str] = ["localhost", "127.0.0.1"]
    API_ORIGIN: str = "http://localhost:8000"
    SESSION_COOKIE_NAME: str = "studyflow_session"
    SESSION_MAX_AGE_SECONDS: int = Field(default=604800, ge=300, le=2592000)
    COOKIE_SECURE: bool = False
    DOCS_ENABLED: bool = False
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    DB_POOL_SIZE: int = Field(default=5, ge=1, le=100)
    DB_MAX_OVERFLOW: int = Field(default=5, ge=0, le=100)
    DB_POOL_RECYCLE: int = Field(default=1800, ge=30)
    DB_POOL_TIMEOUT: int = Field(default=10, ge=1, le=60)
    DB_COMMAND_TIMEOUT: int = Field(default=30, ge=1, le=300)
    RATE_LIMIT_DEFAULT: str = "240/minute"
    RATE_LIMIT_AUTH: str = "6/minute"
    RATE_LIMIT_SIGNUP: str = "10/hour"
    RATE_LIMIT_RESETS: str = "5/hour"
    MAX_REQUEST_BYTES: int = Field(default=524288, ge=1024, le=10485760)

    @property
    def request_origins(self) -> list[str]:
        origins = [*self.ALLOWED_ORIGINS, self.API_ORIGIN]
        api = urlsplit(self.API_ORIGIN)
        if self.APP_ENV == "development" and api.hostname in {"localhost", "127.0.0.1"}:
            # Swagger can be opened with either local hostname, on the configured API port.
            alias = "127.0.0.1" if api.hostname == "localhost" else "localhost"
            port = f":{api.port}" if api.port is not None else ""
            origins.append(f"{api.scheme}://{alias}{port}")
        return list(dict.fromkeys(origins))

    @field_validator("DATABASE_URL")
    @classmethod
    def postgres_url(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().startswith("postgresql+asyncpg://"):
            raise ValueError("DATABASE_URL must use postgresql+asyncpg://")
        return value

    @field_validator("ALLOWED_ORIGINS")
    @classmethod
    def origins(cls, values: list[str]) -> list[str]:
        if not values:
            raise ValueError("At least one explicit origin is required.")
        for value in values:
            parsed = urlsplit(value)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or "*" in value
                or parsed.path not in {"", "/"}
                or parsed.query
                or parsed.fragment
                or parsed.username
            ):
                raise ValueError(
                    "Origins must be explicit HTTP(S) origins, without paths or wildcards."
                )
            _ = parsed.port
        return list(dict.fromkeys(value.rstrip("/") for value in values))

    @field_validator("API_ORIGIN")
    @classmethod
    def api_origin(cls, value: str) -> str:
        return cls.origins([value])[0]

    @field_validator("ALLOWED_METHODS", "ALLOWED_HEADERS", "TRUSTED_HOSTS")
    @classmethod
    def explicit_values(cls, values: list[str]) -> list[str]:
        if not values or any(not value.strip() or "*" in value for value in values):
            raise ValueError("Explicit non-wildcard values are required.")
        return [value.strip() for value in values]

    @field_validator(
        "RATE_LIMIT_DEFAULT", "RATE_LIMIT_AUTH", "RATE_LIMIT_SIGNUP", "RATE_LIMIT_RESETS"
    )
    @classmethod
    def valid_rate_limit(cls, value: str) -> str:
        from limits import parse

        if parse(value).amount < 1:
            raise ValueError("Rate limits require a positive request allowance.")
        return value

    @model_validator(mode="after")
    def production_policy(self) -> Self:
        if self.APP_ENV == "production":
            if not self.COOKIE_SECURE or not self.SESSION_COOKIE_NAME.startswith("__Host-"):
                raise ValueError(
                    "Production requires COOKIE_SECURE=true and a __Host- session cookie."
                )
            if not urlsplit(self.DATABASE_URL.get_secret_value()).password:
                raise ValueError("Production DATABASE_URL requires database authentication.")
            if any(
                not value.startswith("https://")
                or urlsplit(value).hostname in {"localhost", "127.0.0.1"}
                for value in self.ALLOWED_ORIGINS + [self.API_ORIGIN]
            ):
                raise ValueError("Production origins must be explicit HTTPS deployment origins.")
            if set(self.TRUSTED_HOSTS) <= {"localhost", "127.0.0.1"}:
                raise ValueError("Production requires deployed TRUSTED_HOSTS.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]
