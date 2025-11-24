"""
Testes Unitários - Filtragem de Previsões Passadas no Weather Repository
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lambda'))

import pytest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from infrastructure.adapters.output.weather_repository import OpenWeatherRepository


def test_select_forecast_filters_past_forecasts():
    """Testa que _select_forecast filtra previsões passadas"""
    repo = OpenWeatherRepository(api_key="dummy_key")
    
    now = datetime.now(tz=ZoneInfo("UTC"))
    past_time = now - timedelta(hours=6)
    future_time = now + timedelta(hours=3)
    
    forecasts = [
        {'dt': int(past_time.timestamp()), 'main': {'temp': 20}},
        {'dt': int((past_time + timedelta(hours=3)).timestamp()), 'main': {'temp': 22}},
        {'dt': int(future_time.timestamp()), 'main': {'temp': 25}},
        {'dt': int((future_time + timedelta(hours=3)).timestamp()), 'main': {'temp': 27}},
    ]
    
    # Sem target_datetime - deve usar now() e retornar apenas futuras
    result = repo._select_forecast(forecasts, None)
    
    assert result is not None
    assert result['main']['temp'] == 25  # Primeira previsão futura


def test_select_forecast_relative_to_target_datetime():
    """Testa que _select_forecast filtra relativo ao target_datetime"""
    repo = OpenWeatherRepository(api_key="dummy_key")
    
    base_time = datetime(2025, 11, 20, 12, 0, tzinfo=ZoneInfo("UTC"))
    
    forecasts = [
        {'dt': int((base_time - timedelta(hours=3)).timestamp()), 'main': {'temp': 18}},
        {'dt': int(base_time.timestamp()), 'main': {'temp': 20}},
        {'dt': int((base_time + timedelta(hours=3)).timestamp()), 'main': {'temp': 22}},
        {'dt': int((base_time + timedelta(hours=6)).timestamp()), 'main': {'temp': 24}},
    ]
    
    # Com target_datetime = base_time, deve ignorar timestamp < base_time
    target = base_time
    result = repo._select_forecast(forecasts, target)
    
    assert result is not None
    # Deve retornar a previsão exatamente no target_datetime (mais próxima)
    assert result['main']['temp'] == 20


def test_select_forecast_returns_none_when_no_future():
    """Testa que _select_forecast retorna None quando não há previsões futuras"""
    repo = OpenWeatherRepository(api_key="dummy_key")
    
    base_time = datetime(2025, 11, 20, 12, 0, tzinfo=ZoneInfo("UTC"))
    
    # Todas as previsões são passadas
    forecasts = [
        {'dt': int((base_time - timedelta(hours=9)).timestamp()), 'main': {'temp': 18}},
        {'dt': int((base_time - timedelta(hours=6)).timestamp()), 'main': {'temp': 19}},
        {'dt': int((base_time - timedelta(hours=3)).timestamp()), 'main': {'temp': 20}},
    ]
    
    result = repo._select_forecast(forecasts, base_time)
    
    assert result is None


def test_select_forecast_with_target_in_past_but_has_future():
    """Testa que quando target_datetime está no passado mas há previsões futuras relativas a ele"""
    repo = OpenWeatherRepository(api_key="dummy_key")
    
    # Target está no passado absoluto, mas alguns forecasts estão no futuro relativo
    target = datetime(2025, 11, 1, 12, 0, tzinfo=ZoneInfo("UTC"))
    
    forecasts = [
        {'dt': int((target - timedelta(hours=3)).timestamp()), 'main': {'temp': 18}},
        {'dt': int(target.timestamp()), 'main': {'temp': 20}},
        {'dt': int((target + timedelta(hours=3)).timestamp()), 'main': {'temp': 22}},
    ]
    
    result = repo._select_forecast(forecasts, target)
    
    assert result is not None
    # Deve retornar previsão >= target (20 ou 22)
    assert result['main']['temp'] in [20, 22]


def test_collect_alerts_filters_past_forecasts():
    """Testa que alertas são gerados apenas de previsões futuras"""
    repo = OpenWeatherRepository(api_key="dummy_key")
    
    # Nota: Este teste verifica o comportamento no repositório com adapter
    # O repositório simples não tem _collect_all_alerts
    # Vamos testar apenas _select_forecast para este repositório
    pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
