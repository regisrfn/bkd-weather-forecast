"""
Test Smart Alert Generation
Verifica que a lógica inteligente usa dados hourly quando disponíveis e complementa com daily
"""
import pytest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from domain.services.alerts_generator import AlertsGenerator


class MockForecast:
    """Mock de forecast para testes"""
    def __init__(self, timestamp, temperature=25.0, wind_speed=10.0, 
                 rain_probability=0, precipitation=0):
        self.timestamp = timestamp
        self.temperature = temperature
        self.wind_speed = wind_speed
        self.wind_direction = 180
        self.rain_probability = rain_probability
        self.precipitation = precipitation
        self.rainfall_intensity = 0
        self.weather_code = 0


@pytest.mark.asyncio
class TestSmartAlertGeneration:
    """Testa a lógica inteligente de combinação hourly + daily"""
    
    async def test_calculate_hourly_day_coverage_full_week(self):
        """Testa cálculo de cobertura com 7 dias completos de dados hourly"""
        brasil_tz = ZoneInfo("America/Sao_Paulo")
        # Usar meia-noite para simplificar cálculo de dias
        now = datetime.now(tz=brasil_tz).replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Criar 168 horas (7 dias) de forecasts
        hourly_forecasts = []
        for hour in range(168):
            ts = now + timedelta(hours=hour)
            hourly_forecasts.append(MockForecast(timestamp=ts))
        
        # Calcular cobertura
        covered_days = AlertsGenerator._calculate_hourly_day_coverage(
            hourly_forecasts=hourly_forecasts,
            target_datetime=now,
            days_limit=7,
            min_hours_per_day=20
        )
        
        # Deve ter cobertura completa (dias 0-6)
        assert covered_days == {0, 1, 2, 3, 4, 5, 6}
    
    async def test_calculate_hourly_day_coverage_partial(self):
        """Testa cálculo de cobertura com apenas 2 dias de dados hourly"""
        brasil_tz = ZoneInfo("America/Sao_Paulo")
        # Usar meia-noite para simplificar cálculo de dias
        now = datetime.now(tz=brasil_tz).replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Criar apenas 48 horas (2 dias) de forecasts
        hourly_forecasts = []
        for hour in range(48):
            ts = now + timedelta(hours=hour)
            hourly_forecasts.append(MockForecast(timestamp=ts))
        
        # Calcular cobertura
        covered_days = AlertsGenerator._calculate_hourly_day_coverage(
            hourly_forecasts=hourly_forecasts,
            target_datetime=now,
            days_limit=7,
            min_hours_per_day=20
        )
        
        # Deve ter cobertura apenas dos 2 primeiros dias
        assert covered_days == {0, 1}
    
    async def test_generate_alerts_uses_all_hourly_when_available(self):
        """Testa que alertas usam todos os dados hourly quando disponíveis"""
        brasil_tz = ZoneInfo("America/Sao_Paulo")
        now = datetime.now(tz=brasil_tz).replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Criar 168 horas (7 dias) de forecasts com vento forte
        hourly_forecasts = []
        for hour in range(168):
            ts = now + timedelta(hours=hour)
            # Vento forte no dia 3 (horas 72-95)
            wind_speed = 60.0 if 72 <= hour < 96 else 10.0
            hourly_forecasts.append(MockForecast(
                timestamp=ts,
                wind_speed=wind_speed
            ))
        
        # Daily forecasts (não devem ser usados se hourly cobre tudo)
        daily_forecasts = []
        for day in range(7):
            ts = now + timedelta(days=day)
            daily_forecasts.append(MockForecast(
                timestamp=ts,
                wind_speed=10.0  # Vento normal (não geraria alerta)
            ))
        
        # Gerar alertas
        alerts = await AlertsGenerator.generate_alerts_for_weather(
            hourly_forecasts=hourly_forecasts,
            daily_forecasts=daily_forecasts,
            target_datetime=now,
            days_limit=7
        )
        
        # Deve ter alertas (vento forte está nos dados hourly)
        assert len(alerts) > 0
        # Verificar que há alerta de vento
        wind_alerts = [a for a in alerts if 'vento' in a.description.lower()]
        assert len(wind_alerts) > 0
    
    async def test_generate_alerts_supplements_with_daily_when_hourly_incomplete(self):
        """Testa que daily complementa dias não cobertos por hourly"""
        brasil_tz = ZoneInfo("America/Sao_Paulo")
        now = datetime.now(tz=brasil_tz).replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Criar apenas 48 horas (2 dias) de forecasts
        hourly_forecasts = []
        for hour in range(48):
            ts = now + timedelta(hours=hour)
            hourly_forecasts.append(MockForecast(
                timestamp=ts,
                wind_speed=10.0  # Vento normal
            ))
        
        # Daily forecasts com vento forte no dia 5
        daily_forecasts = []
        for day in range(7):
            ts = now + timedelta(days=day)
            wind_speed = 60.0 if day == 5 else 10.0
            daily_forecasts.append(MockForecast(
                timestamp=ts,
                wind_speed=wind_speed
            ))
        
        # Gerar alertas
        alerts = await AlertsGenerator.generate_alerts_for_weather(
            hourly_forecasts=hourly_forecasts,
            daily_forecasts=daily_forecasts,
            target_datetime=now,
            days_limit=7
        )
        
        # Deve ter alertas (vento forte está no dia 5 do daily)
        assert len(alerts) > 0
        # Verificar que há alerta de vento
        wind_alerts = [a for a in alerts if 'vento' in a.description.lower()]
        assert len(wind_alerts) > 0
    
    async def test_generate_alerts_empty_lists(self):
        """Testa comportamento com listas vazias"""
        alerts = await AlertsGenerator.generate_alerts_for_weather(
            hourly_forecasts=[],
            daily_forecasts=[],
            target_datetime=datetime.now(),
            days_limit=7
        )
        
        assert alerts == []
    
    async def test_calculate_hourly_day_coverage_respects_min_hours(self):
        """Testa que min_hours_per_day é respeitado"""
        brasil_tz = ZoneInfo("America/Sao_Paulo")
        # Usar meia-noite para simplificar cálculo de dias
        now = datetime.now(tz=brasil_tz).replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Criar 30 horas de forecasts (dia 0 completo + dia 1 parcial)
        hourly_forecasts = []
        for hour in range(30):
            ts = now + timedelta(hours=hour)
            hourly_forecasts.append(MockForecast(timestamp=ts))
        
        # Com min 20 horas, apenas dia 0 deve estar coberto
        covered_days = AlertsGenerator._calculate_hourly_day_coverage(
            hourly_forecasts=hourly_forecasts,
            target_datetime=now,
            days_limit=7,
            min_hours_per_day=20
        )
        
        assert 0 in covered_days
        # Dia 1 tem apenas 6 horas (24-30), não deve estar coberto
        assert 1 not in covered_days
