"""
Use Case: Get Regional Weather Data
Refatorado para usar providers desacoplados com batch optimization
"""
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime
from zoneinfo import ZoneInfo
from ddtrace import tracer

from domain.entities.daily_forecast import DailyForecast
from domain.entities.hourly_forecast import HourlyForecast
from domain.entities.weather import Weather
from domain.exceptions import CityNotFoundException, CoordinatesNotFoundException
from domain.constants import Cache
from application.ports.output.weather_provider_port import IWeatherProvider
from domain.services.alerts_generator import AlertsGenerator
from application.ports.input.get_regional_weather_port import IGetRegionalWeatherUseCase
from application.ports.output.city_repository_port import ICityRepository
from domain.value_objects.daily_aggregated_metrics import DailyAggregatedMetrics
from shared.config.logger_config import get_logger

logger = get_logger(child=True)


class GetRegionalWeatherUseCase(IGetRegionalWeatherUseCase):
    """
    Async use case: Get weather data for multiple cities in parallel
    
    OTIMIZADO:
    - True I/O parallelism com asyncio
    - 50-100+ requisições simultâneas
    - Semaphore para controle de concorrência
    - Individual error handling
    """
    
    def __init__(
        self,
        city_repository: ICityRepository,
        weather_provider: IWeatherProvider
    ):
        self.city_repository = city_repository
        self.weather_provider = weather_provider
    
    @tracer.wrap(resource="use_case.async_regional_weather")
    async def execute(
        self,
        city_ids: List[str],
        target_datetime: Optional[datetime] = None
    ) -> List[Weather]:
        """
        Execute use case asynchronously com asyncio.gather()
        
        Strategy:
        1. Semaphore(50) para limitar concorrência
        2. asyncio.gather() para executar TODAS cidades em paralelo
        3. Error handling individual (uma falha não afeta outras)
        
        Args:
            city_ids: Lista de IDs de cidades
            target_datetime: Datetime específico para forecast (opcional)
        
        Returns:
            List[Weather]: Dados meteorológicos (apenas sucessos)
        """
        logger.info(
            "Iniciando busca regional",
            total_cities=len(city_ids),
            provider=self.weather_provider.provider_name,
            target_date=target_datetime.isoformat() if target_datetime else "next_available"
        )

        prefetched_hourly, prefetched_daily = await self._prefetch_openmeteo_cache(city_ids)
        hourly_writes: Dict[str, Any] = {}
        daily_writes: Dict[str, Any] = {}
        
        # Fetch all cities in parallel
        weather_data = await self._fetch_all_cities(
            city_ids=city_ids,
            target_datetime=target_datetime,
            prefetched_hourly=prefetched_hourly,
            prefetched_daily=prefetched_daily,
            hourly_writes=hourly_writes,
            daily_writes=daily_writes
        )

        # Persist cache writes em batch para reduzir chamadas ao DynamoDB
        await asyncio.gather(
            self._batch_set_openmeteo_cache(hourly_writes, Cache.TTL_OPENMETEO_HOURLY),
            self._batch_set_openmeteo_cache(daily_writes, Cache.TTL_OPENMETEO_DAILY)
        )
        
        # Calculate success rate
        success_rate = (len(weather_data) / len(city_ids) * 100) if city_ids else 0
        
        logger.info(
            "Busca regional concluída",
            processed=len(weather_data),
            requested=len(city_ids),
            success_rate=f"{success_rate:.1f}%"
        )
        
        return weather_data
    
    async def _fetch_all_cities(
        self,
        city_ids: List[str],
        target_datetime: Optional[datetime],
        prefetched_hourly: Dict[str, Any],
        prefetched_daily: Dict[str, Any],
        hourly_writes: Dict[str, Any],
        daily_writes: Dict[str, Any]
    ) -> List[Weather]:
        """
        Fetch weather data para todas cidades em paralelo
        
        Args:
            city_ids: IDs das cidades
            target_datetime: Datetime alvo
            prefetched_hourly: cache pré-carregado para hourly
            prefetched_daily: cache pré-carregado para daily
            hourly_writes: buffer para batch set hourly
            daily_writes: buffer para batch set daily
        
        Returns:
            Lista de Weather entities (apenas sucessos)
        """
        semaphore = asyncio.Semaphore(50)
        
        # Criar tasks para todas as cidades
        tasks = [
            self._fetch_single_city_with_semaphore(
                city_id,
                target_datetime,
                semaphore,
                prefetched_hourly,
                prefetched_daily,
                hourly_writes,
                daily_writes
            )
            for city_id in city_ids
        ]
        
        # Execute all in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful results
        weather_data = [
            result for result in results
            if isinstance(result, Weather)
        ]
        
        # Log errors
        errors = [
            result for result in results
            if isinstance(result, Exception)
        ]
        if errors:
            logger.warning(
                f"Failed to fetch {len(errors)} cities",
                error_count=len(errors)
            )
        
        return weather_data
    
    async def _fetch_single_city_with_semaphore(
        self,
        city_id: str,
        target_datetime: Optional[datetime],
        semaphore: asyncio.Semaphore,
        prefetched_hourly: Dict[str, Any],
        prefetched_daily: Dict[str, Any],
        hourly_writes: Dict[str, Any],
        daily_writes: Dict[str, Any]
    ) -> Weather:
        """
        Fetch weather para uma cidade com semaphore
        
        Args:
            city_id: ID da cidade
            target_datetime: Datetime alvo
            semaphore: Semaphore para controle de concorrência
            prefetched_hourly: cache pré-carregado para hourly
            prefetched_daily: cache pré-carregado para daily
            hourly_writes: buffer para batch set hourly
            daily_writes: buffer para batch set daily
        
        Returns:
            Weather entity
        
        Raises:
            Exception: Se falhar (capturado no gather)
        """
        async with semaphore:
            # Delay de 50ms entre requests para evitar rate limiting
            return await self._fetch_single_city(
                city_id,
                target_datetime,
                prefetched_hourly,
                prefetched_daily,
                hourly_writes,
                daily_writes
            )
    
    async def _fetch_single_city(
        self,
        city_id: str,
        target_datetime: Optional[datetime],
        prefetched_hourly: Dict[str, Any],
        prefetched_daily: Dict[str, Any],
        hourly_writes: Dict[str, Any],
        daily_writes: Dict[str, Any]
    ) -> Weather:
        """
        Fetch weather para uma cidade
        
        Args:
            city_id: ID da cidade
            target_datetime: Datetime alvo
            prefetched_hourly: cache pré-carregado para hourly
            prefetched_daily: cache pré-carregado para daily
            hourly_writes: buffer para batch set hourly
            daily_writes: buffer para batch set daily
        
        Returns:
            Weather entity
        
        Raises:
            CityNotFoundException: Se cidade não encontrada
            CoordinatesNotFoundException: Se sem coordenadas
        """
        # Get city
        city = self.city_repository.get_by_id(city_id)
        if not city:
            raise CityNotFoundException(
                f"City not found",
                details={"city_id": city_id}
            )
        
        # Validate coordinates
        if not city.has_coordinates():
            raise CoordinatesNotFoundException(
                f"City has no coordinates",
                details={"city_id": city_id, "city_name": city.name}
            )
        
        # Fetch hourly and daily data once, reuse for current weather + alerts
        hourly_task = self.weather_provider.get_hourly_forecast(
            latitude=city.latitude,
            longitude=city.longitude,
            city_id=city.id,
            hours=168,  # 7 dias - usado para current weather + alertas
            prefetched_data=prefetched_hourly,
            cache_writes=hourly_writes
        )
        
        daily_task = self.weather_provider.get_daily_forecast(
            latitude=city.latitude,
            longitude=city.longitude,
            city_id=city.id,
            days=16,  # 16 dias para consistência de cache entre rotas
            prefetched_data=prefetched_daily,
            cache_writes=daily_writes
        )
        
        hourly_forecasts, daily_forecasts = await asyncio.gather(hourly_task, daily_task)
        
        # Extrair current weather dos dados hourly já buscados
        weather = self.weather_provider.extract_current_weather_from_hourly(
            hourly_forecasts=hourly_forecasts,
            daily_forecasts=daily_forecasts if daily_forecasts else None,
            city_id=city.id,
            city_name=city.name,
            target_datetime=target_datetime
        )
        
        # Gerar alertas usando dados já buscados
        alerts = await AlertsGenerator.generate_alerts_for_weather(
            hourly_forecasts=hourly_forecasts if hourly_forecasts else [],
            daily_forecasts=daily_forecasts if daily_forecasts else [],
            target_datetime=target_datetime,
            days_limit=7
        )
        
        if alerts:
            object.__setattr__(weather, 'weather_alert', alerts)

        daily_aggregates = self._build_daily_aggregates(
            hourly_forecasts=hourly_forecasts if hourly_forecasts else [],
            daily_forecasts=daily_forecasts if daily_forecasts else [],
            target_datetime=target_datetime
        )
        if daily_aggregates:
            weather.daily_aggregates = daily_aggregates
        
        return weather

    def _build_daily_aggregates(
        self,
        hourly_forecasts: List[HourlyForecast],
        daily_forecasts: List[DailyForecast],
        target_datetime: Optional[datetime]
    ) -> Optional[DailyAggregatedMetrics]:
        """
        Calcula métricas agregadas para o dia alvo (chuva, intensidade e vento)
        """
        if not hourly_forecasts and not daily_forecasts:
            return None

        target_dt = target_datetime or datetime.now(tz=ZoneInfo("America/Sao_Paulo"))
        if target_dt.tzinfo is None:
            target_dt = target_dt.replace(tzinfo=ZoneInfo("America/Sao_Paulo"))
        target_date = target_dt.date().isoformat()

        hourly_for_day = [
            forecast for forecast in hourly_forecasts
            if forecast.timestamp.startswith(target_date)
        ]

        rain_volume = sum(f.precipitation for f in hourly_for_day) if hourly_for_day else 0.0
        rain_intensity_max = max((float(f.rainfall_intensity) for f in hourly_for_day), default=0.0)
        rain_probability_max = max((float(f.precipitation_probability) for f in hourly_for_day), default=0.0)
        wind_speed_max_hourly = max((float(f.wind_speed) for f in hourly_for_day), default=0.0)

        daily_match = next(
            (d for d in daily_forecasts if d.date == target_date),
            None
        )

        temp_min = daily_match.temp_min if daily_match else 0.0
        temp_max = daily_match.temp_max if daily_match else 0.0

        if daily_match:
            rain_volume = max(rain_volume, daily_match.precipitation_mm)
            rain_intensity_max = max(rain_intensity_max, float(daily_match.rainfall_intensity))
            rain_probability_max = max(rain_probability_max, float(daily_match.rain_probability))
            wind_speed_max = max(wind_speed_max_hourly, float(daily_match.wind_speed_max))
        else:
            wind_speed_max = wind_speed_max_hourly

        metrics = DailyAggregatedMetrics(
            date=target_date,
            rain_volume=rain_volume,
            rain_intensity_max=rain_intensity_max,
            rain_probability_max=rain_probability_max,
            wind_speed_max=wind_speed_max,
            temp_min=temp_min,
            temp_max=temp_max
        )
        logger.info(
            "Daily aggregates calculados",
            date=target_date,
            rain_volume=metrics.rain_volume,
            rain_intensity_max=metrics.rain_intensity_max,
            rain_probability_max=metrics.rain_probability_max,
            wind_speed_max=metrics.wind_speed_max,
            temp_min=metrics.temp_min,
            temp_max=metrics.temp_max
        )
        return metrics

    async def _prefetch_openmeteo_cache(
        self,
        city_ids: List[str]
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Pré-carrega cache hourly/daily em batch para reduzir chamadas ao DynamoDB
        """
        cache = getattr(self.weather_provider, "cache", None)
        if not cache or not cache.is_enabled() or not city_ids:
            return {}, {}

        batch_get = getattr(cache, "batch_get", None)
        if not batch_get or not asyncio.iscoroutinefunction(batch_get):
            return {}, {}

        hourly_keys = [f"{Cache.PREFIX_OPENMETEO_HOURLY}{city_id}" for city_id in city_ids]
        daily_keys = [f"{Cache.PREFIX_OPENMETEO_DAILY}{city_id}" for city_id in city_ids]

        hourly_result, daily_result = await asyncio.gather(
            batch_get(hourly_keys),
            batch_get(daily_keys)
        )

        return hourly_result or {}, daily_result or {}

    async def _batch_set_openmeteo_cache(
        self,
        items: Dict[str, Any],
        ttl_seconds: int
    ) -> None:
        """
        Salva dados no cache em batch (usa TTL específico por tipo)
        """
        cache = getattr(self.weather_provider, "cache", None)
        if not cache or not cache.is_enabled() or not items:
            return

        batch_set = getattr(cache, "batch_set", None)
        if not batch_set or not asyncio.iscoroutinefunction(batch_set):
            return

        await batch_set(items, ttl_seconds=ttl_seconds)
