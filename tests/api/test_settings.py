import pytest
from pydantic import ValidationError

from gir_api.settings import ApiSettings


def test_settings_defaults() -> None:
    settings = ApiSettings(_env_file=None)
    assert settings.generate_timeout_seconds == 15.0
    assert settings.validate_timeout_seconds == 5.0
    assert settings.render_timeout_seconds == 10.0
    assert settings.max_input_chars == 20_000
    assert settings.log_level == "INFO"


def test_settings_read_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEOMETRYOS_GENERATE_TIMEOUT_SECONDS", "21")
    monkeypatch.setenv("GEOMETRYOS_MAX_INPUT_CHARS", "5000")
    monkeypatch.setenv("GEOMETRYOS_LOG_LEVEL", "debug")
    settings = ApiSettings(_env_file=None)
    assert settings.generate_timeout_seconds == 21
    assert settings.max_input_chars == 5000
    assert settings.log_level == "DEBUG"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("generate_timeout_seconds", 0),
        ("validate_timeout_seconds", -1),
        ("render_timeout_seconds", 121),
        ("max_input_chars", 0),
        ("max_input_chars", 20_001),
        ("log_level", "TRACE"),
    ],
)
def test_settings_reject_invalid_values(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        ApiSettings(**{field: value}, _env_file=None)
