"""
Use Case: Get Regional Weather Data
Refatorado para usar providers desacoplados com batch optimization
"""
import asyncio
from typing import Optional, List
from datetime import datetime
from ddtrace import tracer

from domain.entities.weather import Weather
from domain.exceptions import CityNotFoundException, CoordinatesNotFoundException
from application.ports.output.weather_provider_port import IWeatherProvider
from domain.services.alerts_generator import AlertsGenerator
from application.ports.input.get_regional_weather_port import IGetRegionalWeatherUseCase
from application.ports.output.city_repository_port import ICityRepository
from infrastructure.adapters.output.providers.openmeteo.openmeteo_provider import OpenMeteoProvider
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
        
        # Fetch all cities in parallel
        weather_data = await self._fetch_all_cities(city_ids, target_datetime)
        
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
        target_datetime: Optional[datetime] = None
    ) -> List[Weather]:
        """
        Fetch weather data para todas cidades em paralelo
        
        Args:
            city_ids: IDs das cidades
            target_datetime: Datetime alvo
        
        Returns:
            Lista de Weather entities (apenas sucessos)
        """
        # Semaphore para limitar concorrência (evitar throttling)
        semaphore = asyncio.Semaphore(50)
        
        # Criar tasks para todas as cidades
        tasks = [
            self._fetch_single_city_with_semaphore(
                city_id,
                target_datetime,
                semaphore
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
        semaphore: asyncio.Semaphore
    ) -> Weather:
        """
        Fetch weather para uma cidade com semaphore
        
        Args:
            city_id: ID da cidade
            target_datetime: Datetime alvo
            semaphore: Semaphore para controle de concorrência
        
        Returns:
            Weather entity
        
        Raises:
            Exception: Se falhar (capturado no gather)
        """
        async with semaphore:
            return await self._fetch_single_city(city_id, target_datetime)
    
    async def _fetch_single_city(
        self,
        city_id: str,
        target_datetime: Optional[datetime]
    ) -> Weather:
        """
        Fetch weather para uma cidade
        
        Args:
            city_id: ID da cidade
            target_datetime: Datetime alvo
        
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
            hours=168  # 7 dias - usado para current weather + alertas
        )
        
        daily_task = self.weather_provider.get_daily_forecast(
            latitude=city.latitude,
            longitude=city.longitude,
            city_id=city.id,
            days=16  # 16 dias para consistência de cache entre rotas
        )
        
        hourly_forecasts, daily_forecasts = await asyncio.gather(hourly_task, daily_task)
        
        # Extrair current weather dos dados hourly já buscados
        weather = OpenMeteoProvider.extract_current_weather_from_hourly(
            hourly_forecasts=hourly_forecasts,
            daily_forecasts=daily_forecasts[:1] if daily_forecasts else None,
            city_id=city.id,
            city_name=city.name,
            target_datetime=target_datetime
        )
        
        # Gerar alertas usando dados já buscados
        alerts = await AlertsGenerator.generate_alerts_for_weather(
            hourly_forecasts=hourly_forecasts[:48] if hourly_forecasts else [],
            daily_forecasts=daily_forecasts if daily_forecasts else [],
            target_datetime=target_datetime,
            days_limit=7
        )
        
        if alerts:
            object.__setattr__(weather, 'weather_alert', alerts)
        
        return weather
