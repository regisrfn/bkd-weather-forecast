"""
Output Adapter: Implementação do Repositório de Dados Meteorológicos
Integração com OpenWeatherMap API (Forecast) com Cache DynamoDB
"""
import requests
import os
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional, List
from ddtrace import tracer
from domain.entities.weather import Weather
from application.ports.output.weather_repository_port import IWeatherRepository
from application.ports.output.cache_repository_port import ICacheRepository

logger = logging.getLogger(__name__)


class OpenWeatherRepository(IWeatherRepository):
    """Repositório de dados meteorológicos usando OpenWeatherMap Forecast API com Cache"""
    
    def __init__(self, api_key: Optional[str] = None, cache_repository: Optional[ICacheRepository] = None):
        """
        Inicializa o repositório
        
        Args:
            api_key: Chave da API OpenWeatherMap (opcional, usa env se não fornecida)
            cache_repository: Repositório de cache (opcional)
        """
        self.api_key = api_key or os.environ.get('OPENWEATHER_API_KEY')
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.cache = cache_repository
        
        if not self.api_key:
            raise ValueError("OPENWEATHER_API_KEY não configurada")
    
    @tracer.wrap(service="weather-forecast", resource="repository.get_current_weather")
    def get_current_weather(self, latitude: float, longitude: float, city_name: str, 
                           target_datetime: Optional[datetime] = None) -> Weather:
        """
        Busca dados meteorológicos (previsão) do OpenWeather com Cache
        
        Estratégia:
        1. Verifica cache DynamoDB por cityId (se cache habilitado)
        2. Se MISS, chama API OpenWeather
        3. Salva resposta completa no cache com TTL de 3 horas
        4. Processa dados e retorna Weather entity
        
        Args:
            latitude: Latitude da cidade
            longitude: Longitude da cidade
            city_name: Nome da cidade
            target_datetime: Data/hora específica para previsão (opcional, usa próxima disponível se None)
        
        Returns:
            Weather: Dados meteorológicos com probabilidade de chuva
        
        Raises:
            Exception: Se a chamada à API falhar ou não houver dados para a data solicitada
        """
        # Nota: cityId será preenchido pelo use case, mas não temos aqui ainda
        # Por enquanto, usamos coordenadas como chave de cache
        cache_key = f"{latitude:.4f}_{longitude:.4f}"
        
        # Tentar buscar do cache primeiro
        data = None
        if self.cache and self.cache.is_enabled():
            data = self.cache.get(cache_key)
            if data:
                logger.info(f"Cache HIT para coordenadas {cache_key}")
        
        # Se não encontrou no cache, chamar API
        if data is None:
            logger.info(f"Cache MISS para coordenadas {cache_key}, chamando API")
            url = f"{self.base_url}/forecast"
            
            params = {
                'lat': latitude,
                'lon': longitude,
                'appid': self.api_key,
                'units': 'metric',
                'lang': 'pt_br'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Salvar no cache (resposta completa)
            if self.cache and self.cache.is_enabled():
                self.cache.set(cache_key, data)
        
        # Processar dados (mesmo fluxo anterior)
        forecast_item = self._select_forecast(data['list'], target_datetime)
        
        if not forecast_item:
            raise ValueError("Nenhuma previsão futura disponível para a data/hora solicitada")
        
        # Extrair dados da previsão selecionada
        weather_code = forecast_item['weather'][0]['id']
        rain_prob = forecast_item.get('pop', 0) * 100  # 0-1 para 0-100%
        wind_speed = forecast_item['wind']['speed'] * 3.6  # m/s para km/h
        forecast_time = datetime.fromtimestamp(forecast_item['dt'], tz=ZoneInfo("UTC"))
        
        # Gerar alertas de TODAS as previsões futuras (não apenas da selecionada)
        weather_alerts = self._collect_all_alerts(data['list'], target_datetime)
        
        # Calcular temperaturas mínima e máxima do DIA INTEIRO
        temp_min_day, temp_max_day = self._get_daily_temp_extremes(data['list'], target_datetime)
        
        # Converter resposta da API para entidade Weather
        return Weather(
            city_id='',  # Será preenchido pelo use case
            city_name=city_name,
            timestamp=forecast_time,
            temperature=forecast_item['main']['temp'],
            humidity=forecast_item['main']['humidity'],
            wind_speed=wind_speed,
            rain_probability=rain_prob,
            rain_1h=forecast_item.get('rain', {}).get('3h', 0) / 3,  # Aproximação de 3h para 1h
            description=forecast_item['weather'][0].get('description', ''),
            feels_like=forecast_item['main'].get('feels_like', 0),
            pressure=forecast_item['main'].get('pressure', 0),
            visibility=forecast_item.get('visibility', 0),
            clouds=forecast_item.get('clouds', {}).get('all', 0),  # Cobertura de nuvens (0-100%)
            weather_alert=weather_alerts,  # Alertas de todas as previsões
            weather_code=weather_code,
            temp_min=temp_min_day,  # Mínima do dia inteiro
            temp_max=temp_max_day   # Máxima do dia inteiro
        )
    
    def _collect_all_alerts(self, forecasts: List[dict], target_datetime: Optional[datetime] = None) -> List:
        """
        Coleta alertas de TODAS as previsões futuras
        Filtra previsões passadas antes de gerar alertas (relativo ao target_datetime)
        Útil para mostrar alertas importantes dos próximos dias
        
        Args:
            forecasts: Lista completa de previsões da API
            target_datetime: Data/hora de referência para filtro (None = agora UTC)
        
        Returns:
            Lista consolidada de alertas únicos (sem duplicatas por code)
        """
        all_alerts = []
        seen_codes = set()
        
        # Determinar data/hora de referência para filtro
        if target_datetime is None:
            reference_datetime = datetime.now(tz=ZoneInfo("UTC"))
        elif target_datetime.tzinfo is not None:
            reference_datetime = target_datetime.astimezone(ZoneInfo("UTC"))
        else:
            reference_datetime = target_datetime.replace(tzinfo=ZoneInfo("UTC"))
        
        # Filtrar apenas previsões futuras relativas ao target_datetime
        future_forecasts = [
            f for f in forecasts
            if datetime.fromtimestamp(f['dt'], tz=ZoneInfo("UTC")) >= reference_datetime
        ]
        
        for forecast_item in future_forecasts:
            weather_code = forecast_item['weather'][0]['id']
            rain_prob = forecast_item.get('pop', 0) * 100
            wind_speed = forecast_item['wind']['speed'] * 3.6
            forecast_time = datetime.fromtimestamp(forecast_item['dt'], tz=ZoneInfo("UTC"))
            
            # Gerar alertas desta previsão
            alerts = Weather.get_weather_alert(
                weather_code=weather_code,
                rain_prob=rain_prob,
                wind_speed=wind_speed,
                forecast_time=forecast_time
            )
            
            # Adicionar apenas alertas que ainda não vimos (por code)
            for alert in alerts:
                if alert.code not in seen_codes:
                    all_alerts.append(alert)
                    seen_codes.add(alert.code)
        
        return all_alerts
    
    def _get_daily_temp_extremes(self, forecasts: List[dict], target_datetime: Optional[datetime]) -> tuple[float, float]:
        """
        Calcula temperaturas mínima e máxima do DIA INTEIRO da data alvo
        
        Args:
            forecasts: Lista de previsões da API
            target_datetime: Data/hora alvo (None = hoje)
        
        Returns:
            Tupla (temp_min, temp_max) do dia inteiro
        """
        if not forecasts:
            return (0.0, 0.0)
        
        # Determinar data alvo
        if target_datetime is None:
            target_date = datetime.now(tz=ZoneInfo("UTC")).date()
        else:
            # Converter para UTC se necessário
            if target_datetime.tzinfo is not None:
                target_datetime_utc = target_datetime.astimezone(ZoneInfo("UTC"))
            else:
                target_datetime_utc = target_datetime.replace(tzinfo=ZoneInfo("UTC"))
            target_date = target_datetime_utc.date()
        
        # Determinar data/hora de referência para filtro
        if target_datetime is None:
            reference_datetime = datetime.now(tz=ZoneInfo("UTC"))
        elif target_datetime.tzinfo is not None:
            reference_datetime = target_datetime.astimezone(ZoneInfo("UTC"))
        else:
            reference_datetime = target_datetime.replace(tzinfo=ZoneInfo("UTC"))
        
        # Filtrar previsões futuras do mesmo dia (relativo ao target_datetime)
        day_forecasts = [
            f for f in forecasts
            if datetime.fromtimestamp(f['dt'], tz=ZoneInfo("UTC")).date() == target_date
            and datetime.fromtimestamp(f['dt'], tz=ZoneInfo("UTC")) >= reference_datetime
        ]
        
        if not day_forecasts:
            # Se não há previsões para o dia, retorna da primeira disponível
            return (forecasts[0]['main']['temp_min'], forecasts[0]['main']['temp_max'])
        
        # Extrair todas as temperaturas do dia
        temps = []
        for f in day_forecasts:
            temps.append(f['main']['temp'])
            temps.append(f['main']['temp_min'])
            temps.append(f['main']['temp_max'])
        
        return (min(temps), max(temps))
    
    def _select_forecast(self, forecasts: List[dict], target_datetime: Optional[datetime]) -> Optional[dict]:
        """
        Seleciona a previsão mais próxima da data/hora solicitada
        Filtra previsões passadas para retornar apenas previsões futuras
        
        Args:
            forecasts: Lista de previsões da API
            target_datetime: Data/hora alvo (None = agora UTC)
        
        Returns:
            Previsão selecionada ou None se não houver previsões futuras
        
        Nota: Busca a previsão MAIS PRÓXIMA do horário solicitado,
        considerando apenas previsões com timestamp >= target_datetime.
        """
        if not forecasts:
            return None
        
        # Determinar data/hora de referência para filtro
        if target_datetime is None:
            reference_datetime = datetime.now(tz=ZoneInfo("UTC"))
        elif target_datetime.tzinfo is not None:
            reference_datetime = target_datetime.astimezone(ZoneInfo("UTC"))
        else:
            reference_datetime = target_datetime.replace(tzinfo=ZoneInfo("UTC"))
        
        # Filtrar apenas previsões futuras (>= reference_datetime)
        future_forecasts = [
            f for f in forecasts
            if datetime.fromtimestamp(f['dt'], tz=ZoneInfo("UTC")) >= reference_datetime
        ]
        
        # Se não há previsões futuras, retornar None
        if not future_forecasts:
            return None
        
        # Encontra previsão MAIS PRÓXIMA usando min() com key function
        closest_forecast = min(
            future_forecasts,
            key=lambda f: abs(
                datetime.fromtimestamp(f['dt'], tz=ZoneInfo("UTC")) - reference_datetime
            ).total_seconds()
        )
        
        return closest_forecast


def get_weather_repository(api_key: Optional[str] = None) -> IWeatherRepository:
    """
    Factory para criar repositório de weather com cache
    Permite facilmente trocar implementação ou adicionar mock
    """
    # Importar aqui para evitar circular dependency
    from infrastructure.adapters.cache.dynamodb_cache_adapter import get_cache_repository
    
    cache = get_cache_repository()
    return OpenWeatherRepository(api_key=api_key, cache_repository=cache)
