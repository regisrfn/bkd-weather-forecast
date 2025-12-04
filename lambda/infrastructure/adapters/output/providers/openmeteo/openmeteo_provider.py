"""Open-Meteo Provider - Implementação do provider para Open-Meteo API"""

import asyncio
from typing import Optional, List
from datetime import datetime
from ddtrace import tracer
import aiohttp
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
import logging

from datetime import datetime as dt
from zoneinfo import ZoneInfo

from application.ports.output.weather_provider_port import IWeatherProvider
from shared.config.logger_config import get_logger

logger = get_logger(child=True)
from domain.entities.weather import Weather
from domain.entities.daily_forecast import DailyForecast
from domain.entities.hourly_forecast import HourlyForecast
from domain.constants import API, Cache
from infrastructure.adapters.output.providers.openmeteo.mappers import OpenMeteoDataMapper
from infrastructure.adapters.output.cache.async_dynamodb_cache import AsyncDynamoDBCache, get_async_cache
from infrastructure.adapters.output.http.aiohttp_session_manager import get_aiohttp_session_manager


class OpenMeteoProvider(IWeatherProvider):
    """
    Provider para Open-Meteo Forecast API
    
    Características:
    - API gratuita sem rate limits agressivos
    - Previsões diárias de até 16 dias
    - Previsões horárias de até 168 horas (7 dias)
    - Dados astronômicos (nascer/pôr do sol, fase lua)
    - Cache DynamoDB com TTL de 1 hora
    - 100% async com aiohttp
    """
    
    def __init__(
        self,
        cache: Optional[AsyncDynamoDBCache] = None
    ):
        """
        Inicializa provider
        
        Args:
            cache: Cache DynamoDB async (usa factory se None)
        """
        self.base_url = API.OPENMETEO_BASE_URL
        self.cache = cache or get_async_cache()
        
        # Usar gerenciador centralizado de sessão HTTP
        self.session_manager = get_aiohttp_session_manager(
            total_timeout=API.HTTP_TIMEOUT_TOTAL,
            connect_timeout=API.HTTP_TIMEOUT_CONNECT,
            sock_read_timeout=API.HTTP_TIMEOUT_READ,
            limit=API.HTTP_CONNECTION_LIMIT,
            limit_per_host=API.HTTP_CONNECTION_LIMIT_PER_HOST,
            ttl_dns_cache=API.DNS_CACHE_TTL
        )
    
    @property
    def provider_name(self) -> str:
        return "OpenMeteo"
    
    @property
    def supports_current_weather(self) -> bool:
        return True  # Via hourly data
    
    @property
    def supports_daily_forecast(self) -> bool:
        return True
    
    @property
    def supports_hourly_forecast(self) -> bool:
        return True
    
    @staticmethod
    def extract_current_weather_from_hourly(
        hourly_forecasts: List[HourlyForecast],
        daily_forecasts: Optional[List[DailyForecast]],
        city_id: str,
        city_name: str,
        target_datetime: Optional[datetime] = None
    ) -> Weather:
        """
        Extrai current weather de dados hourly já buscados
        Evita buscar 168 horas novamente
        
        Args:
            hourly_forecasts: Lista de previsões horárias já buscadas
            daily_forecasts: Lista de previsões diárias (para temp_min/max)
            city_id: ID da cidade
            city_name: Nome da cidade
            target_datetime: Data/hora de referência (padrão: agora)
        
        Returns:
            Weather entity com dados atuais
        """
        
        if not hourly_forecasts:
            raise ValueError("Nenhuma previsão horária disponível")
        
        # Se target_datetime não fornecido, usar agora
        if target_datetime is None:
            target_datetime = dt.now(tz=ZoneInfo("America/Sao_Paulo"))
        elif target_datetime.tzinfo is None:
            target_datetime = target_datetime.replace(tzinfo=ZoneInfo("America/Sao_Paulo"))
        
        now = dt.now(tz=ZoneInfo("America/Sao_Paulo"))
        
        # Encontrar forecast mais próximo do target_datetime
        # REGRA: Se target_datetime está no passado, retornar primeiro forecast futuro
        # REGRA: Se target_datetime está no futuro, retornar o mais próximo disponível
        closest_forecast = None
        min_diff = None
        
        # Filtrar apenas forecasts futuros em relação ao momento atual
        future_forecasts = []
        for forecast in hourly_forecasts:
            forecast_dt = dt.fromisoformat(forecast.timestamp)
            if forecast_dt.tzinfo is None:
                forecast_dt = forecast_dt.replace(tzinfo=ZoneInfo("America/Sao_Paulo"))
            
            # Apenas considerar forecasts futuros (não retornar previsões passadas)
            if forecast_dt >= now:
                future_forecasts.append((forecast, forecast_dt))
        
        # Se não há forecasts futuros, usar o último disponível
        if not future_forecasts:
            closest_forecast = hourly_forecasts[-1]
        else:
            # Se target_datetime está no passado, retornar o primeiro forecast futuro
            if target_datetime < now:
                # Ordenar por timestamp e pegar o primeiro
                future_forecasts.sort(key=lambda x: x[1])
                closest_forecast = future_forecasts[0][0]
            else:
                # Se target_datetime está no futuro, buscar o mais próximo
                for forecast, forecast_dt in future_forecasts:
                    diff = abs((forecast_dt - target_datetime).total_seconds())
                    
                    if min_diff is None or diff < min_diff:
                        min_diff = diff
                        closest_forecast = forecast
        
        if closest_forecast is None:
            closest_forecast = hourly_forecasts[0]
        
        # Extrair temp_min, temp_max e rain_accumulated_day do daily forecast do dia
        temp_min = 0.0
        temp_max = 0.0
        rain_accumulated_day = 0.0
        
        if daily_forecasts:
            # Pegar o dia correspondente ao target_datetime
            target_date = target_datetime.date().isoformat()
            for daily in daily_forecasts:
                if daily.date == target_date:
                    temp_min = daily.temp_min
                    temp_max = daily.temp_max
                    rain_accumulated_day = daily.precipitation_mm
                    break
            # Se não encontrou correspondência, usar o primeiro dia
            if temp_min == 0.0 and temp_max == 0.0 and daily_forecasts:
                temp_min = daily_forecasts[0].temp_min
                temp_max = daily_forecasts[0].temp_max
                rain_accumulated_day = daily_forecasts[0].precipitation_mm
        
        # Converter para Weather entity
        return OpenMeteoDataMapper.map_hourly_to_weather(
            hourly_forecast=closest_forecast,
            city_id=city_id,
            city_name=city_name,
            temp_min=temp_min,
            temp_max=temp_max,
            rain_accumulated_day=rain_accumulated_day
        )
    
    @tracer.wrap(resource="openmeteo.get_current_weather")
    async def get_current_weather(
        self,
        latitude: float,
        longitude: float,
        city_id: str,
        city_name: str,
        target_datetime: Optional[datetime] = None,
        include_daily_alerts: bool = False  # Compatibilidade com interface
    ) -> Weather:
        """
        OpenMeteo fornece dados atuais via hourly forecast
        Busca forecast hourly e extrai hora mais próxima
        Também busca temperaturas min/max do dia
        """
        # Buscar hourly e daily em paralelo
        hourly_task = self.get_hourly_forecast(
            latitude=latitude,
            longitude=longitude,
            city_id=city_id,
            hours=168  # 7 dias para garantir que temos a hora solicitada
        )
        
        daily_task = self.get_daily_forecast(
            latitude=latitude,
            longitude=longitude,
            city_id=city_id,
            days=1  # Apenas o dia atual para pegar min/max
        )
        
        hourly_forecasts, daily_forecasts = await asyncio.gather(hourly_task, daily_task)
        
        # Usar método estático para extrair current weather
        return self.extract_current_weather_from_hourly(
            hourly_forecasts=hourly_forecasts,
            daily_forecasts=daily_forecasts,
            city_id=city_id,
            city_name=city_name,
            target_datetime=target_datetime
        )
    
    @tracer.wrap(resource="openmeteo.get_daily_forecast")
    async def get_daily_forecast(
        self,
        latitude: float,
        longitude: float,
        city_id: str,
        days: int = 16
    ) -> List[DailyForecast]:
        """
        Busca previsões diárias do Open-Meteo
        
        Flow:
        1. Tenta cache DynamoDB (prefix: openmeteo_)
        2. Se MISS: chama API Open-Meteo (async HTTP)
        3. Salva no cache (TTL 1h)
        4. Processa e retorna List[DailyForecast]
        """
        if days < 1 or days > 16:
            raise ValueError(f"days deve estar entre 1 e 16, recebeu {days}")
        
        cache_key = f"{Cache.PREFIX_OPENMETEO_DAILY}{city_id}"
        
        # 🔍 Tentar cache primeiro
        data = None
        if self.cache and self.cache.is_enabled():
            data = await self.cache.get(cache_key)
        
        # 📡 Cache MISS: chamar API
        if data is None:
            url = f"{self.base_url}/forecast"
            params = {
                'latitude': latitude,
                'longitude': longitude,
                'daily': ','.join([
                    'temperature_2m_max',
                    'temperature_2m_min',
                    'apparent_temperature_max',
                    'apparent_temperature_min',
                    'precipitation_sum',
                    'precipitation_probability_mean',
                    'wind_speed_10m_max',
                    'wind_direction_10m_dominant',
                    'uv_index_max',
                    'sunrise',
                    'sunset',
                    'precipitation_hours'
                ]),
                'timezone': 'America/Sao_Paulo',
                'forecast_days': days
            }
            
            session = await self.session_manager.get_session()
            
            # Retry com exponential backoff para rate limiting
            @retry(
                retry=retry_if_exception_type((aiohttp.ClientResponseError, asyncio.TimeoutError)),
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=1, min=1, max=4),
                before_sleep=before_sleep_log(logger, logging.WARNING),
                reraise=True
            )
            async def fetch_with_retry():
                async with session.get(url, params=params) as response:
                    # Apenas retry em rate limit (429) e service unavailable (503)
                    if response.status in [429, 503]:
                        raise aiohttp.ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status
                        )
                    response.raise_for_status()
                    return await response.json()
            
            data = await fetch_with_retry()
            
            # 💾 Salvar no cache
            if self.cache and self.cache.is_enabled():
                await self.cache.set(cache_key, data, ttl_seconds=Cache.TTL_OPENMETEO_DAILY)
        
        # 🔄 Processar dados usando mapper de infrastructure
        return OpenMeteoDataMapper.map_daily_response_to_forecasts(data)
    
    @tracer.wrap(resource="openmeteo.get_hourly_forecast")
    async def get_hourly_forecast(
        self,
        latitude: float,
        longitude: float,
        city_id: str,
        hours: int = 168
    ) -> List[HourlyForecast]:
        """
        Busca previsões horárias do Open-Meteo
        
        Flow:
        1. Tenta cache DynamoDB (prefix: openmeteo_hourly_)
        2. Se MISS: chama API Open-Meteo (async HTTP)
        3. Salva no cache (TTL 1h)
        4. Processa e retorna List[HourlyForecast]
        """
        cache_key = f"{Cache.PREFIX_OPENMETEO_HOURLY}{city_id}"
        
        # 🔍 Tentar cache primeiro
        data = None
        if self.cache and self.cache.is_enabled():
            data = await self.cache.get(cache_key)
        
        # 📡 Cache MISS: chamar API
        if data is None:
            url = f"{self.base_url}/forecast"
            params = {
                'latitude': latitude,
                'longitude': longitude,
                'hourly': ','.join([
                    'temperature_2m',
                    'apparent_temperature',
                    'precipitation',
                    'precipitation_probability',
                    'relative_humidity_2m',
                    'wind_speed_10m',
                    'wind_direction_10m',
                    'cloud_cover',
                    'pressure_msl',
                    'visibility',
                    'uv_index',
                    'is_day',
                    'weather_code'
                ]),
                'timezone': 'America/Sao_Paulo',
                'forecast_days': min(16, (hours // 24) + 1)
            }
            
            session = await self.session_manager.get_session()
            
            # Retry com exponential backoff para rate limiting
            @retry(
                retry=retry_if_exception_type((aiohttp.ClientResponseError, asyncio.TimeoutError)),
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=1, min=1, max=4),
                before_sleep=before_sleep_log(logger, logging.WARNING),
                reraise=True
            )
            async def fetch_with_retry():
                async with session.get(url, params=params) as response:
                    # Apenas retry em rate limit (429) e service unavailable (503)
                    if response.status in [429, 503]:
                        raise aiohttp.ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status
                        )
                    response.raise_for_status()
                    return await response.json()
            
            data = await fetch_with_retry()
            
            # 💾 Salvar no cache
            if self.cache and self.cache.is_enabled():
                await self.cache.set(cache_key, data, ttl_seconds=Cache.TTL_OPENMETEO_HOURLY)
        
        # 🔄 Processar dados usando mapper de infrastructure
        return OpenMeteoDataMapper.map_hourly_response_to_forecasts(data, max_hours=hours)


# Factory singleton
_provider_instance = None


def get_openmeteo_provider(
    cache: Optional[AsyncDynamoDBCache] = None
) -> OpenMeteoProvider:
    """
    Factory para obter singleton do provider
    Reutiliza entre invocações Lambda (warm starts)
    """
    global _provider_instance
    
    if _provider_instance is None:
        _provider_instance = OpenMeteoProvider(cache=cache)
    
    return _provider_instance
