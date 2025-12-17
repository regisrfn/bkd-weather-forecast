"""
Integration test: warm-up ping followed by real request.
Validates short-circuit response and reuses warmed event loop.
"""
import json

from infrastructure.adapters.input import lambda_handler as handler_module


def test_warmup_then_detailed_forecast(mock_context):
    """Simula ping de warm-up e depois uma chamada real."""
    original_loop = handler_module._global_event_loop

    try:
        # Simular cold start
        handler_module._global_event_loop = None

        warmup_event = {"warmup": True}
        warmup_response = handler_module.lambda_handler(warmup_event, mock_context)

        assert warmup_response["statusCode"] == 200
        warmup_body = json.loads(warmup_response["body"])
        assert warmup_body.get("warmup") is True

        warmed_loop = handler_module._global_event_loop
        assert warmed_loop is not None

        # Chamada real deve reutilizar loop aquecido
        event = {
            "httpMethod": "GET",
            "path": "/api/weather/city/3543204/detailed",
            "pathParameters": {"city_id": "3543204"},
            "queryStringParameters": None,
            "headers": {},
            "requestContext": {"identity": {"sourceIp": "127.0.0.1"}},
        }

        response = handler_module.lambda_handler(event, mock_context)

        assert response["statusCode"] == 200
        assert handler_module._global_event_loop is warmed_loop

    finally:
        # Restaurar loop original para não impactar outros testes
        handler_module._global_event_loop = original_loop
