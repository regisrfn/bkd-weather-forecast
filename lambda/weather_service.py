"""
Serviço de dados climáticos para os municípios.
Usa OpenWeatherMap API ou mock data.
"""
import random
from datetime import datetime, timezone
from typing import Dict, Optional
import os

try:
    from openweather_service import OpenWeatherService
    OPENWEATHER_AVAILABLE = True
except ImportError:
    OPENWEATHER_AVAILABLE = False
    print("⚠️  OpenWeatherService não disponível")

# Configuração
USE_OPENWEATHER = os.environ.get('USE_OPENWEATHER', 'false').lower() == 'true'
OPENWEATHER_API_KEY = os.environ.get('OPENWEATHER_API_KEY', '')
import requests
import random
from datetime import datetime
from typing import Dict, Any, List
from config import OPENWEATHER_API_KEY, OPENWEATHER_BASE_URL


def get_weather_from_openweather(lat: float, lon: float) -> Optional[Dict]:
    """
    Busca dados reais do OpenWeatherMap usando o serviço dedicado.
    
    Args:
        lat: Latitude
        lon: Longitude
    
    Returns:
        Dict com dados climáticos ou None se falhar
    """
    if not OPENWEATHER_AVAILABLE or not OPENWEATHER_API_KEY:
        return None
    
    try:
        service = OpenWeatherService(OPENWEATHER_API_KEY)
        weather = service.get_current_weather(lat, lon)
        
        # Converter para formato esperado pelo Lambda
        return {
            'temperature': weather['temperature'],
            'humidity': weather['humidity'],
            'windSpeed': weather['wind_speed'],
            'rainfallIntensity': min(weather['rain_1h'] * 10, 100),  # mm para percentual aproximado
        }
        
    except Exception as e:
        print(f"Erro ao buscar OpenWeather: {e}")
        return None


def _parse_openweather_response(city_id: str, city_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parseia resposta da OpenWeatherMap API
    """
    main = data.get('main', {})
    wind = data.get('wind', {})
    rain = data.get('rain', {})
    
    # Calcular intensidade de chuva (0-100%)
    rain_1h = rain.get('1h', 0)  # mm de chuva na última hora
    rainfall_intensity = min((rain_1h / 10) * 100, 100)  # Normalizar para 0-100%
    
    return {
        'cityId': city_id,
        'cityName': city_name,
        'temperature': main.get('temp', 20.0),
        'humidity': main.get('humidity', 60.0),
        'windSpeed': wind.get('speed', 10.0) * 3.6,  # m/s para km/h
        'rainfallIntensity': rainfall_intensity,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }


def _generate_mock_weather(city_id: str, city_name: str) -> Dict[str, Any]:
    """
    Gera dados climáticos mockados para desenvolvimento
    """
    return {
        'cityId': city_id,
        'cityName': city_name,
        'temperature': round(random.uniform(18.0, 30.0), 1),
        'humidity': round(random.uniform(40.0, 85.0), 1),
        'windSpeed': round(random.uniform(5.0, 25.0), 1),
        'rainfallIntensity': round(random.uniform(0.0, 100.0), 1),
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }


def get_weather_for_city(city_id: str, cities_db: Dict[str, Dict]) -> Optional[Dict]:
    """
    Busca dados climáticos para uma cidade
    
    Args:
        city_id: Código IBGE da cidade
        cities_db: Dicionário com dados das cidades
    
    Returns:
        dict: Dados climáticos ou None se cidade não encontrada
    """
    city = cities_db.get(city_id)
    
    if not city:
        return None
    
    # Tentar OpenWeather primeiro se configurado
    if USE_OPENWEATHER and city.get('latitude') and city.get('longitude'):
        weather_data = get_weather_from_openweather(city['latitude'], city['longitude'])
        
        if weather_data:
            weather_data['cityId'] = city_id
            weather_data['cityName'] = city['name']
            weather_data['timestamp'] = datetime.now(timezone.utc).isoformat()
            return weather_data
    
    # Fallback para mock
    return {
        'cityId': city_id,
        'cityName': city['name'],
        'temperature': round(random.uniform(18.0, 30.0), 1),
        'humidity': round(random.uniform(40.0, 85.0), 1),
        'windSpeed': round(random.uniform(5.0, 25.0), 1),
        'rainfallIntensity': round(random.uniform(0.0, 100.0), 1),
        'timestamp': datetime.now(timezone.utc).isoformat()
    }


def get_regional_weather(city_ids: List[str], cities_db: Dict[str, Dict]) -> List[Dict]:
    """
    Busca dados climáticos para múltiplas cidades
    
    Args:
        city_ids: Lista de códigos IBGE
        cities_db: Dicionário com dados das cidades
    
    Returns:
        list: Lista com dados climáticos de todas as cidades
    """
    weather_data = []
    
    for city_id in city_ids:
        city = cities_db.get(city_id)
        if city:
            weather = get_weather_for_city(
                city_id=city['id'],
                city_name=city['name'],
                lat=city['latitude'],
                lon=city['longitude']
            )
            weather_data.append(weather)
    
    return weather_data
