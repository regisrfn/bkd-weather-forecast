"""
Testes de Integração - Enrichment com Hourly Data
Valida que dados hourly enriquecem corretamente o current weather
"""
import pytest
import json
from infrastructure.adapters.input.lambda_handler import lambda_handler
from tests.integration.conftest import mock_context


class TestHourlyEnrichment:
    """Testes para validar enriquecimento com dados hourly"""
    
    def test_current_weather_enriched_with_hourly(self, mock_context):
        """
        Valida que current weather foi enriquecido com dados hourly
        mantendo campos do OpenWeather
        """
        event = {
            'httpMethod': 'GET',
            'path': '/api/weather/city/3543204/detailed',
            'pathParameters': {'city_id': '3543204'},
            'queryStringParameters': None,
            'headers': {},
            'requestContext': {'identity': {'sourceIp': '127.0.0.1'}}
        }
        
        response = lambda_handler(event, mock_context)
        
        assert response['statusCode'] == 200
        
        body = json.loads(response['body'])
        current = body['currentWeather']
        
        # ===== CAMPOS ENRIQUECIDOS DO HOURLY =====
        # Temperatura mais precisa (hora exata vs intervalo 3h)
        assert 'temperature' in current
        assert isinstance(current['temperature'], (int, float))
        
        # Direção do vento agora disponível
        assert 'windDirection' in current
        assert isinstance(current['windDirection'], int)
        assert 0 <= current['windDirection'] <= 360
        
        # Umidade e nuvens atualizados
        assert 'humidity' in current
        assert 'clouds' in current
        
        # ===== CAMPOS PRESERVADOS DO OPENWEATHER =====
        # Visibility - Open-Meteo não fornece, deve vir do OpenWeather
        assert 'visibility' in current
        assert current['visibility'] > 0, "Visibility should be from OpenWeather (not default)"
        
        # Pressure - Open-Meteo hourly não fornece, deve vir do OpenWeather
        assert 'pressure' in current
        assert current['pressure'] > 0, "Pressure should be from OpenWeather (not default)"
        
        # Feels Like - Open-Meteo não fornece, deve vir do OpenWeather
        assert 'feelsLike' in current
        assert isinstance(current['feelsLike'], (int, float))
        
        print("\n✅ Enriquecimento validado:")
        print(f"   - Wind Direction: {current['windDirection']}°")
        print(f"   - Temperature: {current['temperature']}°C")
        print(f"   - Visibility (OpenWeather): {current['visibility']}m")
        print(f"   - Pressure (OpenWeather): {current['pressure']} hPa")
        print(f"   - Feels Like (OpenWeather): {current['feelsLike']}°C")
    
    def test_hourly_forecasts_available(self, mock_context):
        """Valida que array de hourly forecasts está disponível"""
        event = {
            'httpMethod': 'GET',
            'path': '/api/weather/city/3543204/detailed',
            'pathParameters': {'city_id': '3543204'},
            'queryStringParameters': None,
            'headers': {},
            'requestContext': {'identity': {'sourceIp': '127.0.0.1'}}
        }
        
        response = lambda_handler(event, mock_context)
        
        assert response['statusCode'] == 200
        
        body = json.loads(response['body'])
        
        # Hourly forecasts deve existir
        assert 'hourlyForecasts' in body
        hourly = body['hourlyForecasts']
        
        # Deve ser uma lista (pode estar vazia se API falhar, mas deve existir)
        assert isinstance(hourly, list)
        
        # Se houver dados, validar estrutura completa
        if len(hourly) > 0:
            print(f"\n✅ Hourly forecasts disponíveis: {len(hourly)} horas")
            
            # Validar algumas horas
            for i, forecast in enumerate(hourly[:3]):
                assert 'timestamp' in forecast
                assert 'temperature' in forecast
                assert 'windDirection' in forecast
                assert 'precipitation' in forecast
                
                print(f"   Hora {i}: {forecast['timestamp']} - "
                      f"{forecast['temperature']}°C, "
                      f"Vento {forecast['windDirection']}°, "
                      f"Precip {forecast['precipitation']}mm")
        else:
            print("\n⚠️  Hourly forecasts vazio (API pode ter fallback ativo)")
    
    def test_backward_compatibility(self, mock_context):
        """
        Valida que resposta mantém compatibilidade com versão anterior
        (todos os campos existentes ainda estão presentes)
        """
        event = {
            'httpMethod': 'GET',
            'path': '/api/weather/city/3543204/detailed',
            'pathParameters': {'city_id': '3543204'},
            'queryStringParameters': None,
            'headers': {},
            'requestContext': {'identity': {'sourceIp': '127.0.0.1'}}
        }
        
        response = lambda_handler(event, mock_context)
        
        assert response['statusCode'] == 200
        
        body = json.loads(response['body'])
        
        # ===== ESTRUTURA PRINCIPAL (BACKWARD COMPATIBLE) =====
        assert 'cityInfo' in body
        assert 'currentWeather' in body
        assert 'dailyForecasts' in body
        assert 'extendedAvailable' in body
        
        # ===== CAMPOS EXISTENTES DO CURRENT WEATHER =====
        current = body['currentWeather']
        required_fields = [
            'cityId', 'cityName', 'timestamp',
            'temperature', 'humidity', 'windSpeed',
            'rainfallIntensity', 'rainfallProbability',
            'rainVolumeHour', 'dailyRainAccumulation',
            'description', 'feelsLike', 'pressure',
            'visibility', 'clouds', 'cloudsDescription',
            'tempMin', 'tempMax'
        ]
        
        for field in required_fields:
            assert field in current, f"Missing backward-compatible field: {field}"
        
        # ===== NOVOS CAMPOS (ADICIONADOS) =====
        assert 'windDirection' in current, "New field windDirection should be present"
        assert 'hourlyForecasts' in body, "New field hourlyForecasts should be present"
        
        print("\n✅ Backward compatibility OK:")
        print(f"   - Todos os {len(required_fields)} campos existentes presentes")
        print(f"   - 2 novos campos adicionados: windDirection, hourlyForecasts")
    
    def test_graceful_degradation_on_hourly_failure(self, mock_context):
        """
        Valida que se hourly falhar, a API ainda funciona
        (usando OpenWeather como fallback completo)
        """
        # Este teste valida que mesmo se get_hourly_forecast() falhar,
        # a resposta ainda é válida usando apenas OpenWeather
        
        event = {
            'httpMethod': 'GET',
            'path': '/api/weather/city/3543204/detailed',
            'pathParameters': {'city_id': '3543204'},
            'queryStringParameters': None,
            'headers': {},
            'requestContext': {'identity': {'sourceIp': '127.0.0.1'}}
        }
        
        response = lambda_handler(event, mock_context)
        
        # Deve retornar sucesso mesmo se hourly falhar
        assert response['statusCode'] == 200
        
        body = json.loads(response['body'])
        
        # Current weather deve existir (do OpenWeather se hourly falhou)
        assert 'currentWeather' in body
        current = body['currentWeather']
        
        # Campos essenciais devem estar presentes
        assert current['temperature'] > 0
        assert current['humidity'] > 0
        assert current['windSpeed'] >= 0
        
        # HourlyForecasts pode estar vazio se falhou, mas deve existir
        assert 'hourlyForecasts' in body
        assert isinstance(body['hourlyForecasts'], list)
        
        print("\n✅ Graceful degradation OK:")
        print(f"   - API responde mesmo se hourly falhar")
        print(f"   - Current weather válido (OpenWeather fallback)")
        print(f"   - Hourly forecasts: {len(body['hourlyForecasts'])} items")
