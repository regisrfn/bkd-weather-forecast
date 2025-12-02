"""Open-Meteo Provider Package"""

from infrastructure.adapters.output.providers.openmeteo.openmeteo_provider import (
    OpenMeteoProvider,
    get_openmeteo_provider
)

__all__ = ['OpenMeteoProvider', 'get_openmeteo_provider']
