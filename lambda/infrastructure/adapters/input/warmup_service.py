"""
Warm-up service to prepare dependencies and short-circuit scheduled pings.
"""
import json
from typing import Callable, Optional, Any

from ddtrace import tracer


class WarmupService:
    def __init__(
        self,
        *,
        logger,
        get_or_create_event_loop: Callable[[], Any],
        run_async: Callable[[Any], Any],
        get_weather_provider_factory: Callable[[], Any],
        get_ibge_geo_provider: Callable[[], Any],
        get_repository: Callable[[], Any],
    ):
        self.logger = logger
        self.get_or_create_event_loop = get_or_create_event_loop
        self.run_async = run_async
        self.get_weather_provider_factory = get_weather_provider_factory
        self.get_ibge_geo_provider = get_ibge_geo_provider
        self.get_repository = get_repository

    @tracer.wrap(resource="warmup.init")
    def warmup_init(self):
        """Prepara dependências pesadas para reuso em warm starts."""
        try:
            # Garantir loop global e carregar singletons síncronos
            self.get_or_create_event_loop()
            weather_factory = self.get_weather_provider_factory()
            weather_provider = weather_factory.get_weather_provider()
            geo_provider = self.get_ibge_geo_provider()
            self.get_repository()
        except Exception as exc:  # pragma: no cover - best-effort
            self.logger.warning("Warm-up init sync step failed", error=str(exc))
            return

        async def preload_async():
            # Criar sessão HTTP e cliente DynamoDB compartilhados
            providers = [weather_provider, geo_provider]
            for provider in providers:
                session_manager = getattr(provider, "session_manager", None)
                if session_manager:
                    await session_manager.get_session()

                cache = getattr(provider, "cache", None)
                client_manager = getattr(cache, "client_manager", None) if cache else None
                if cache and cache.is_enabled() and client_manager:
                    await client_manager.get_client()

        try:
            self.run_async(preload_async())
        except Exception as exc:  # pragma: no cover - best-effort
            self.logger.warning("Warm-up init async step failed", error=str(exc))

    @tracer.wrap(resource="warmup.handle_ping")
    def handle_warmup_ping(self, event: Optional[dict]):
        """
        Warm-up short-circuit para pings agendados (EventBridge/cron).
        """
        if not isinstance(event, dict):
            return None

        if not (event.get("warmup") or event.get("source") == "aws.events"):
            return None

        self.logger.info("Warm-up ping recebido")
        self.warmup_init()
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"ok": True, "warmup": True})
        }
