from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, computed_field, field_validator
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

    @field_validator("cors_allowed_origins")
    @classmethod
    def validate_cors_allowed_origins(cls, value: str) -> str:
        _parse_cors_origins(value)
        return value

    @computed_field
    @property
    def parsed_cors_allowed_origins(self) -> tuple[str, ...]:
        return _parse_cors_origins(self.cors_allowed_origins)


def _parse_cors_origins(value: str) -> tuple[str, ...]:
    origins: list[str] = []
    seen: set[str] = set()
    for raw_origin in value.split(","):
        origin = raw_origin.strip()
        if not origin:
            continue
        if origin in {"*", "null"}:
            raise ValueError("CORS origins must be explicit HTTP(S) origins.")
        parsed = urlsplit(origin)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError(f"Invalid CORS origin: {origin!r}.")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("CORS origins must not contain credentials.")
        if parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
            raise ValueError("CORS origins must not contain paths, queries, or fragments.")
        canonical = origin[:-1] if origin.endswith("/") else origin
        if canonical not in seen:
            seen.add(canonical)
            origins.append(canonical)
    if len(origins) > _MAX_CORS_ORIGINS:
        raise ValueError(f"At most {_MAX_CORS_ORIGINS} CORS origins are allowed.")
    return tuple(origins)


@lru_cache(maxsize=1)
def get_settings() -> ApiSettings:
    return ApiSettings()
