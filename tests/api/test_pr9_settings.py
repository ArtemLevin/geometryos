import pytest
from pydantic import ValidationError

from gir_api.settings import ApiSettings


def test_cors_settings_default_to_disabled() -> None:
    settings = ApiSettings(_env_file=None)
    assert settings.parsed_cors_allowed_origins == ()
    assert settings.cors_max_age_seconds == 600


def test_cors_origins_are_trimmed_deduplicated_and_canonicalized() -> None:
    settings = ApiSettings(
        cors_allowed_origins=(
            " HTTP://LOCALHOST:5173/, http://localhost:5173, https://example.com "
        ),
        _env_file=None,
    )
    assert settings.parsed_cors_allowed_origins == (
        "http://localhost:5173",
        "https://example.com",
    )


@pytest.mark.parametrize(
    "origin",
    [
        "*",
        "null",
        "ftp://localhost:5173",
        "http://user:password@localhost:5173",
        "http://localhost:5173/path",
        "http://localhost:5173?query=yes",
        "http://localhost:5173#fragment",
        "http://localhost:invalid",
    ],
)
def test_cors_origins_reject_unsafe_values(origin: str) -> None:
    with pytest.raises(ValidationError):
        ApiSettings(cors_allowed_origins=origin, _env_file=None)
