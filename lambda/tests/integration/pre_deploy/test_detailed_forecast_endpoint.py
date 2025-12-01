"""
Integration Tests: Detailed Forecast Endpoint
Testes de integração sem mocks - testam fluxo completo com APIs reais
"""
import pytest
import json
from infrastructure.adapters.input.lambda_handler import lambda_handler
from tests.integration.conftest import mock_context


class TestDetailedForecastEndpoint:
    """Integration tests for GET /api/weather/city/{cityId}/detailed"""
    
    def test_detailed_forecast_success(self, mock_context):
        """Test successful detailed forecast retrieval with real API calls"""
        event = {
            'httpMethod': 'GET',
            'path': '/api/weather/city/3543204/detailed',
            'pathParameters': {'city_id': '3543204'},
            'queryStringParameters': None,
            'headers': {},
            'requestContext': {'identity': {'sourceIp': '127.0.0.1'}}
        }
        
        response = lambda_handler(event, mock_context)
        
        # Assertions
        assert response['statusCode'] == 200
        
        body = json.loads(response['body'])
        
        # Validar estrutura da resposta
        assert 'cityInfo' in body, "Response should contain cityInfo"
        assert 'currentWeather' in body, "Response should contain currentWeather"
        assert 'dailyForecasts' in body, "Response should contain dailyForecasts"
        assert 'extendedAvailable' in body, "Response should contain extendedAvailable"
        
        # Validar cityInfo
        city_info = body['cityInfo']
        assert city_info['cityId'] == '3543204'
        assert city_info['cityName'] == 'Ribeirão do Sul'
        
        # Validar currentWeather
        current = body['currentWeather']
        assert 'temperature' in current
        assert 'humidity' in current
        assert 'windSpeed' in current
        assert 'windDirection' in current, "Should contain wind direction"
        assert 'timestamp' in current
        assert 'visibility' in current, "Should preserve OpenWeather visibility"
        assert 'pressure' in current, "Should preserve OpenWeather pressure"
        assert 'feelsLike' in current, "Should preserve OpenWeather feels_like"
        
        # Validar tipos e ranges
        assert isinstance(current['windDirection'], int), "windDirection should be int"
        assert 0 <= current['windDirection'] <= 360, "windDirection should be 0-360 degrees"
        
        # Log informações sobre alertas (para debug)
        print(f"\n=== CURRENT WEATHER DEBUG ===")
        print(f"Timestamp: {current.get('timestamp', 'N/A')}")
        print(f"Temperature: {current.get('temperature', 'N/A')}°C")
        print(f"Precipitation: {current.get('rainfallIntensity', 'N/A')} mm/h")
        
        if 'weatherAlert' in current:
            alerts = current['weatherAlert']
            print(f"Number of alerts: {len(alerts)}")
            for alert in alerts:
                print(f"  {alert.get('code', 'N/A')}: {alert.get('description', 'N/A')} @ {alert.get('timestamp', 'N/A')}")
        else:
            print("No weatherAlert field found")
        print("="*50)
        
        # Validar hourlyForecasts (novo campo)
        assert 'hourlyForecasts' in body, "Response should contain hourlyForecasts"
        hourly = body['hourlyForecasts']
        assert isinstance(hourly, list), "hourlyForecasts should be a list"
        
        # Se houver dados hourly, validar estrutura
        if len(hourly) > 0:
            first_hourly = hourly[0]
            assert 'timestamp' in first_hourly
            assert 'temperature' in first_hourly
            assert 'precipitation' in first_hourly
            assert 'precipitationProbability' in first_hourly
            assert 'humidity' in first_hourly
            assert 'windSpeed' in first_hourly
            assert 'windDirection' in first_hourly
            assert 'cloudCover' in first_hourly
            assert 'weatherCode' in first_hourly
            
            # Validar tipos
            assert isinstance(first_hourly['windDirection'], int)
            assert 0 <= first_hourly['windDirection'] <= 360
        
        # Validar dailyForecasts
        daily = body['dailyForecasts']
        assert isinstance(daily, list), "dailyForecasts should be a list"
        assert len(daily) > 0, "Should have at least one daily forecast"
        
        # Validar estrutura de cada previsão diária
        first_day = daily[0]
        assert 'date' in first_day
        assert 'tempMax' in first_day
        assert 'tempMin' in first_day
        assert 'precipitationMm' in first_day
        assert 'rainProbability' in first_day
        assert 'windSpeedMax' in first_day
        assert 'windDirection' in first_day, "Should contain wind direction"
        assert 'uvIndex' in first_day
        assert 'sunrise' in first_day
        assert 'sunset' in first_day
        
        # Validar tipos de dados
        assert isinstance(first_day['windDirection'], int), "windDirection should be int"
        assert 0 <= first_day['windDirection'] <= 360, "windDirection should be 0-360 degrees"
        assert isinstance(first_day['uvIndex'], (int, float)), "uvIndex should be numeric"
        
    def test_detailed_forecast_city_not_found(self, mock_context):
        """Test error when city is not found"""
        event = {
            'httpMethod': 'GET',
            'path': '/api/weather/city/9999999/detailed',
            'pathParameters': {'city_id': '9999999'},
            'queryStringParameters': None,
            'headers': {},
            'requestContext': {'identity': {'sourceIp': '127.0.0.1'}}
        }
        
        response = lambda_handler(event, mock_context)
        
        # Deve retornar 404
        assert response['statusCode'] == 404
        
        body = json.loads(response['body'])
        assert body['type'] == 'CityNotFoundException'
        assert 'message' in body
    
    def test_detailed_forecast_invalid_city_id(self, mock_context):
        """Test error with invalid city ID format"""
        event = {
            'httpMethod': 'GET',
            'path': '/api/weather/city/invalid/detailed',
            'pathParameters': {'city_id': 'invalid'},
            'queryStringParameters': None,
            'headers': {},
            'requestContext': {'identity': {'sourceIp': '127.0.0.1'}}
        }
        
        response = lambda_handler(event, mock_context)
        
        # ValueError agora é capturado e retorna 400
        assert response['statusCode'] == 400
        
        body = json.loads(response['body'])
        assert 'type' in body
        assert body['type'] == 'ValidationError'
        assert 'message' in body
    
    def test_detailed_forecast_with_date_param(self, mock_context):
        """Test detailed forecast with specific date parameter"""
        event = {
            'httpMethod': 'GET',
            'path': '/api/weather/city/3543204/detailed',
            'pathParameters': {'city_id': '3543204'},
            'queryStringParameters': {'date': '2025-12-01'},
            'headers': {},
            'requestContext': {'identity': {'sourceIp': '127.0.0.1'}}
        }
        
        response = lambda_handler(event, mock_context)
        
        assert response['statusCode'] == 200
        
        body = json.loads(response['body'])
        assert 'dailyForecasts' in body
        assert len(body['dailyForecasts']) > 0

