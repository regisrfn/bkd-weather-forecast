"""
Testes Unitários - Filtragem de Previsões Passadas no Weather Adapter
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lambda'))

import pytest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from infrastructure.adapters.output.weather_repository import OpenWeatherRepository


def test_collect_all_alerts_filters_relative_to_target():
    """Testa que _collect_all_alerts filtra previsões relativas ao target_datetime"""
    repo = OpenWeatherRepository(api_key="dummy_key", cache_repository=None)
    
    base_time = datetime(2025, 11, 20, 12, 0, tzinfo=ZoneInfo("UTC"))
    
    forecasts = [
        {
            'dt': int((base_time - timedelta(hours=3)).timestamp()),
            'weather': [{'id': 501}],  # Rain
            'wind': {'speed': 10},
            'pop': 0.8
        },
        {
            'dt': int(base_time.timestamp()),
            'weather': [{'id': 501}],
            'wind': {'speed': 10},
            'pop': 0.8
        },
        {
            'dt': int((base_time + timedelta(hours=3)).timestamp()),
            'weather': [{'id': 200}],  # Storm
            'wind': {'speed': 15},
            'pop': 0.9
        },
    ]
    
    # Com target_datetime = base_time, deve ignorar alertas de forecasts < base_time
    alerts = repo._collect_all_alerts(forecasts, base_time)
    
    # Deve ter alertas apenas das previsões >= base_time (2 previsões)
    # Como há tempestade em uma delas, deve ter pelo menos um alerta
    assert len(alerts) > 0
    
    # Verificar que todos os alertas têm timestamp >= base_time
    for alert in alerts:
        assert alert.timestamp >= base_time.astimezone(ZoneInfo("America/Sao_Paulo"))


def test_collect_all_alerts_without_target_uses_now():
    """Testa que _collect_all_alerts usa now() quando target_datetime é None"""
    repo = OpenWeatherRepository(api_key="dummy_key", cache_repository=None)
    
    now = datetime.now(tz=ZoneInfo("UTC"))
    
    forecasts = [
        {
            'dt': int((now - timedelta(hours=3)).timestamp()),
            'weather': [{'id': 501}],
            'wind': {'speed': 10},
            'pop': 0.8
        },
        {
            'dt': int((now + timedelta(hours=3)).timestamp()),
            'weather': [{'id': 200}],  # Storm
            'wind': {'speed': 15},
            'pop': 0.9
        },
    ]
    
    # Sem target_datetime - deve usar now()
    alerts = repo._collect_all_alerts(forecasts, None)
    
    # Deve ter alertas apenas da previsão futura
    assert len(alerts) > 0


def test_get_daily_temp_extremes_filters_future():
    """Testa que _get_daily_temp_extremes considera apenas previsões futuras"""
    repo = OpenWeatherRepository(api_key="dummy_key", cache_repository=None)
    
    base_time = datetime(2025, 11, 20, 12, 0, tzinfo=ZoneInfo("UTC"))
    
    forecasts = [
        {
            'dt': int((base_time - timedelta(hours=3)).timestamp()),
            'main': {'temp': 15, 'temp_min': 14, 'temp_max': 16}
        },
        {
            'dt': int(base_time.timestamp()),
            'main': {'temp': 20, 'temp_min': 19, 'temp_max': 21}
        },
        {
            'dt': int((base_time + timedelta(hours=3)).timestamp()),
            'main': {'temp': 25, 'temp_min': 24, 'temp_max': 26}
        },
    ]
    
    # Com target_datetime = base_time
    temp_min, temp_max = repo._get_daily_temp_extremes(forecasts, base_time)
    
    # Deve considerar apenas previsões >= base_time (20 e 25)
    # Não deve incluir 15 (que é passado)
    assert temp_min >= 19  # Mínima das previsões futuras
    assert temp_max <= 26  # Máxima das previsões futuras


def test_select_forecast_adapter_filters_past():
    """Testa que _select_forecast no adapter também filtra previsões passadas"""
    repo = OpenWeatherRepository(api_key="dummy_key", cache_repository=None)
    
    base_time = datetime(2025, 11, 20, 12, 0, tzinfo=ZoneInfo("UTC"))
    
    forecasts = [
        {'dt': int((base_time - timedelta(hours=6)).timestamp()), 'main': {'temp': 18}},
        {'dt': int((base_time - timedelta(hours=3)).timestamp()), 'main': {'temp': 19}},
        {'dt': int(base_time.timestamp()), 'main': {'temp': 20}},
        {'dt': int((base_time + timedelta(hours=3)).timestamp()), 'main': {'temp': 22}},
    ]
    
    result = repo._select_forecast(forecasts, base_time)
    
    assert result is not None
    assert result['main']['temp'] == 20  # Previsão no target_datetime


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
