from typing import Any

from gir_api.models import ValidateGirV1Response


def test_tutorboard_validate_canonical_and_legacy(client: Any, contract_json: Any) -> None:
    for name in ("validate-canonical", "validate-legacy"):
        response = client.post(
            "/api/v1/validate-gir",
            json=contract_json(f"{name}.request.json"),
            headers={"X-Request-ID": "tutorboard-contract"},
        )
        assert response.status_code == 200
        assert response.json() == contract_json(f"{name}.response.json")
        parsed = ValidateGirV1Response.model_validate(response.json())
        assert parsed.schema_version == "0.2.0"
        assert parsed.canonical_gir.schema_version == "0.2.0"
        assert "version" not in response.json()["canonical_gir"]


def test_unknown_gir_version_is_rejected(client: Any, contract_json: Any) -> None:
    payload = contract_json("validate-canonical.request.json")
    payload["schema_version"] = "99.0.0"
    response = client.post("/api/v1/validate-gir", json=payload)
    assert response.status_code == 422
    assert response.json()["code"] == "request_validation_failed"
