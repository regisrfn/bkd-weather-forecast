"""
Integration test: POST /api/geo/municipalities
Executa via lambda_handler (sem mocks) para garantir batch de malhas
"""
import json

from infrastructure.adapters.input.lambda_handler import lambda_handler
from tests.integration.conftest import build_api_gateway_event


def test_post_geo_municipalities_success(mock_context):
    """Deve retornar malhas para múltiplos municípios válidos"""
    city_ids = ["3510153", "3543204"]
    event = build_api_gateway_event(
        method="POST",
        path="/api/geo/municipalities",
        resource="/api/geo/municipalities",
        body={"cityIds": city_ids},
    )

    response = lambda_handler(event, mock_context)

    assert response["statusCode"] == 200

    body = json.loads(response["body"])
    assert isinstance(body, dict)

    for city_id in city_ids:
        assert city_id in body
        mesh = body[city_id]
        assert isinstance(mesh, dict)
        assert mesh.get("type") in ("FeatureCollection", "Feature")


def test_post_geo_municipalities_missing_city_returns_404(mock_context):
    """Deve retornar 404 quando cidade não existe no repositório"""
    event = build_api_gateway_event(
        method="POST",
        path="/api/geo/municipalities",
        resource="/api/geo/municipalities",
        body={"cityIds": ["0000000"]},
    )

    response = lambda_handler(event, mock_context)

    assert response["statusCode"] == 404
