from typing import Any


def test_operational_contracts(client: Any, contract_json: Any) -> None:
    health = client.get("/health", headers={"X-Request-ID": "tutorboard-contract"})
    ready = client.get("/ready", headers={"X-Request-ID": "tutorboard-contract"})
    assert health.status_code == 200
    assert health.json() == contract_json("health.response.json")
    assert ready.status_code == 200
    assert ready.json() == contract_json("readiness.response.json")
    assert ready.headers["Cache-Control"] == "no-store"
    assert health.headers["X-Request-ID"] == "tutorboard-contract"
    assert ready.headers["X-Request-ID"] == "tutorboard-contract"
