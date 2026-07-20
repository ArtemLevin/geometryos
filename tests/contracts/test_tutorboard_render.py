from typing import Any

from gir_api.models import RenderSvgV1Response, RenderTikzV1Response


def test_tutorboard_render_fixtures_execute(client: Any, contract_json: Any) -> None:
    cases = [
        ("render-svg", "/api/v1/render/svg", RenderSvgV1Response),
        ("render-tikz", "/api/v1/render/tikz", RenderTikzV1Response),
    ]
    for name, path, model in cases:
        response = client.post(path, json=contract_json(f"{name}.request.json"))
        assert response.status_code == 200
        assert response.json() == contract_json(f"{name}.response.json")
        model.model_validate(response.json())
