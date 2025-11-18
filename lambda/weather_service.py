"""
Serviço para buscar dados climáticos
"""
import requests
import random
from datetime import datetime
from typing import Dict, Any, List
from config import OPENWEATHER_API_KEY, OPENWEATHER_BASE_URL


def get_weather_for_city(city_id: str, city_name: str, lat: float, lon: float) -> Dict[str, Any]:
    """
    Busca dados climáticos para uma cidade
    
    Se OPENWEATHER_API_KEY não estiver configurada, retorna dados mockados
    
    Args:
        city_id: Código IBGE da cidade
        city_name: Nome da cidade
        lat: Latitude
        lon: Longitude
    
    Returns:
        dict: Dados climáticos da cidade
    """
    
    # Se não tiver API key, retorna dados mockados
    if not OPENWEATHER_API_KEY or OPENWEATHER_API_KEY == '':
        return _generate_mock_weather(city_id, city_name)
    
    try:
        # Chamada real para OpenWeatherMap API
        response = requests.get(
            OPENWEATHER_BASE_URL,
            params={
                'lat': lat,
                'lon': lon,
                'appid': OPENWEATHER_API_KEY,
                'units': 'metric',
                'lang': 'pt_br'
            },
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            return _parse_openweather_response(city_id, city_name, data)
        else:
            # Em caso de erro, retorna dados mockados
            return _generate_mock_weather(city_id, city_name)
            
    except Exception as e:
        print(f"Erro ao buscar dados climáticos: {e}")
        return _generate_mock_weather(city_id, city_name)


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


def get_regional_weather(city_ids: List[str], cities_db: Dict[str, Dict]) -> List[Dict[str, Any]]:
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
