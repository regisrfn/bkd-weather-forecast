"""
Serviço de integração com API de previsão do tempo OpenWeatherMap
"""
import requests
import json
from typing import Dict, List, Optional
from datetime import datetime
import os


class WeatherAPIService:
    """Serviço principal de previsão do tempo"""
    
    def __init__(self, openweather_api_key: Optional[str] = None):
        """
        Inicializa o serviço de clima
        
        Args:
            openweather_api_key: Chave da API OpenWeatherMap (opcional)
        """
        self.openweather_key = openweather_api_key or os.environ.get('OPENWEATHER_API_KEY')
        self.openweather_base = "https://api.openweathermap.org/data/2.5"
        
    
    def get_current_weather(self, lat: float, lon: float, municipality_name: str = None) -> Dict:
        """
        Obtém clima atual de um município
        
        Args:
            lat: Latitude
            lon: Longitude
            municipality_name: Nome do município (para logs)
        
        Returns:
            dict: Dados do clima atual
        """
        if self.openweather_key:
            try:
                return self._get_openweather_current(lat, lon, municipality_name)
            except Exception as e:
                print(f"⚠️  OpenWeatherMap falhou: {e}")
                # Retornar dados mockados em caso de erro
                return self._generate_mock_weather(lat, lon, municipality_name)
        
        # Se não houver API key, retornar dados mockados
        return self._generate_mock_weather(lat, lon, municipality_name)
    
    
    def get_forecast(self, lat: float, lon: float, days: int = 5) -> List[Dict]:
        """
        Obtém previsão do tempo para os próximos dias
        
        Args:
            lat: Latitude
            lon: Longitude
            days: Número de dias (máximo 5 no plano gratuito)
        
        Returns:
            list: Lista com previsão diária
        """
        if not self.openweather_key:
            print("⚠️  API key do OpenWeatherMap não configurada")
            return []
        
        try:
            url = f"{self.openweather_base}/forecast"
            
            params = {
                'lat': lat,
                'lon': lon,
                'appid': self.openweather_key,
                'units': 'metric',
                'lang': 'pt_br',
                'cnt': min(days * 8, 40)  # 8 previsões por dia (a cada 3h)
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Agrupar por dia
            daily_forecast = self._group_forecast_by_day(data['list'])
            
            return daily_forecast[:days]
            
        except Exception as e:
            print(f"❌ Erro ao buscar previsão: {e}")
            return []
    
    
    def _get_openweather_current(self, lat: float, lon: float, name: str = None) -> Dict:
        """Busca clima atual do OpenWeatherMap"""
        url = f"{self.openweather_base}/weather"
        
        params = {
            'lat': lat,
            'lon': lon,
            'appid': self.openweather_key,
            'units': 'metric',
            'lang': 'pt_br'
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        return {
            'source': 'OpenWeatherMap',
            'municipality_name': name,
            'latitude': lat,
            'longitude': lon,
            'timestamp': datetime.now().isoformat(),
            'temperature': data['main']['temp'],
            'feels_like': data['main']['feels_like'],
            'temp_min': data['main']['temp_min'],
            'temp_max': data['main']['temp_max'],
            'humidity': data['main']['humidity'],
            'pressure': data['main']['pressure'],
            'wind_speed': data['wind']['speed'] * 3.6,  # m/s para km/h
            'wind_deg': data['wind'].get('deg', 0),
            'clouds': data['clouds']['all'],
            'rain_1h': data.get('rain', {}).get('1h', 0),
            'weather_main': data['weather'][0]['main'],
            'weather_description': data['weather'][0]['description'],
            'weather_icon': data['weather'][0]['icon']
        }
    
    
    
    def _generate_mock_weather(self, lat: float, lon: float, name: str = None, 
                               source: str = 'Mock') -> Dict:
        """Gera dados climáticos mockados para testes"""
        import random
        
        # Usar coordenadas como seed para consistência
        random.seed(int(abs(lat * 1000) + abs(lon * 1000)))
        
        temp = random.uniform(18, 32)
        
        return {
            'source': source,
            'municipality_name': name,
            'latitude': lat,
            'longitude': lon,
            'timestamp': datetime.now().isoformat(),
            'temperature': round(temp, 1),
            'feels_like': round(temp + random.uniform(-2, 2), 1),
            'temp_min': round(temp - random.uniform(2, 5), 1),
            'temp_max': round(temp + random.uniform(2, 5), 1),
            'humidity': random.randint(40, 90),
            'pressure': random.randint(1010, 1025),
            'wind_speed': round(random.uniform(5, 25), 1),
            'wind_deg': random.randint(0, 360),
            'clouds': random.randint(0, 100),
            'rain_1h': round(random.uniform(0, 10), 1) if random.random() > 0.7 else 0,
            'weather_main': random.choice(['Clear', 'Clouds', 'Rain', 'Drizzle']),
            'weather_description': random.choice(['céu limpo', 'nublado', 'chuva leve', 'parcialmente nublado']),
            'weather_icon': '01d'
        }
    
    
    def _group_forecast_by_day(self, forecast_list: List[Dict]) -> List[Dict]:
        """Agrupa previsão de 3h em previsão diária"""
        days = {}
        
        for item in forecast_list:
            date = datetime.fromtimestamp(item['dt']).date()
            
            if date not in days:
                days[date] = {
                    'date': date.isoformat(),
                    'temp_min': item['main']['temp_min'],
                    'temp_max': item['main']['temp_max'],
                    'humidity': item['main']['humidity'],
                    'wind_speed': item['wind']['speed'] * 3.6,
                    'rain': 0,
                    'weather': item['weather'][0]['description'],
                    'icon': item['weather'][0]['icon'],
                    'samples': 1
                }
            else:
                day_data = days[date]
                day_data['temp_min'] = min(day_data['temp_min'], item['main']['temp_min'])
                day_data['temp_max'] = max(day_data['temp_max'], item['main']['temp_max'])
                day_data['humidity'] += item['main']['humidity']
                day_data['wind_speed'] += item['wind']['speed'] * 3.6
                day_data['rain'] += item.get('rain', {}).get('3h', 0)
                day_data['samples'] += 1
        
        # Calcular médias
        result = []
        for date, data in sorted(days.items()):
            result.append({
                'date': data['date'],
                'temp_min': round(data['temp_min'], 1),
                'temp_max': round(data['temp_max'], 1),
                'humidity': round(data['humidity'] / data['samples']),
                'wind_speed': round(data['wind_speed'] / data['samples'], 1),
                'rain_total': round(data['rain'], 1),
                'weather': data['weather'],
                'icon': data['icon']
            })
        
        return result

