from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from gir_api.constants import MAX_GENERATE_INPUT_CHARS

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
_MAX_CORS_ORIGINS = 32


class ApiSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="GEOMETRYOS_",
        case_sensitive=False,
        extra="ignore",
    )

    generate_timeout_seconds: float = Field(default=15.0, gt=0, le=300)
    validate_timeout_seconds: float = Field(default=5.0, gt=0, le=60)
    render_timeout_seconds: float = Field(default=10.0, gt=0, le=120)
    max_input_chars: int = Field(
        default=MAX_GENERATE_INPUT_CHARS,
        ge=1,
        le=MAX_GENERATE_INPUT_CHARS,
    )
    log_level: LogLevel = "INFO"
    cors_allowed_origins: str = ""
    cors_max_age_seconds: int = Field(default=600, ge=0, le=86_400)

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, value: object) -> object:
        return value.upper() if isinstance(value, str) else value

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def validate_cors_allowed_origins(cls, value: object) -> str:
        if value is None:
            return ""
        if not isinstance(value, str):
            raise ValueError("CORS allowed origins must be a comma-separated string.")

        origins: list[str] = []
        for raw_origin in value.split(","):
            candidate = raw_origin.strip()
            if not candidate:
                continue
            if candidate in {"*", "null"}:
                raise ValueError("Wildcard and null CORS origins are forbidden.")
            parsed = urlsplit(candidate)
            if parsed.scheme.lower() not in {"http", "https"} or parsed.hostname is None:
                raise ValueError(f"Invalid CORS origin: {candidate!r}.")
            if parsed.username is not None or parsed.password is not None:
                raise ValueError("CORS origins must not contain credentials.")
            if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
                raise ValueError("CORS origins must not contain paths, queries, or fragments.")
            try:
                _ = parsed.port
            except ValueError as exc:
                raise ValueError(f"Invalid CORS origin port: {candidate!r}.") from exc
            normalized = f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"
            if normalized not in origins:
                origins.append(normalized)

        if len(origins) > _MAX_CORS_ORIGINS:
            raise ValueError(f"At most {_MAX_CORS_ORIGINS} CORS origins are allowed.")
        return ",".join(origins)

    @property
    def parsed_cors_allowed_origins(self) -> tuple[str, ...]:
        if not self.cors_allowed_origins:
            return ()
        return tuple(self.cors_allowed_origins.split(","))


@lru_cache(maxsize=1)
def get_settings() -> ApiSettings:
    return ApiSettings()
