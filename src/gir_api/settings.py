from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from gir_api.constants import MAX_GENERATE_INPUT_CHARS

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


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

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, value: object) -> object:
        return value.upper() if isinstance(value, str) else value


@lru_cache(maxsize=1)
def get_settings() -> ApiSettings:
    return ApiSettings()
