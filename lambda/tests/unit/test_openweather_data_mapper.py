"""
Testes Unitários - OpenWeatherDataMapper
Testa a geração de alertas a partir de forecasts do OpenWeather
"""
import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from infrastructure.adapters.output.providers.openweather.mappers.openweather_data_mapper import OpenWeatherDataMapper
from domain.alerts.primitives import WeatherAlert


class TestOpenWeatherDataMapperAlertsGeneration:
    """Testa a geração de alertas do OpenWeather"""

    def test_generate_alerts_empty_forecasts(self):
        """Deve retornar lista vazia para forecasts vazios"""
        brasil_tz = ZoneInfo("America/Sao_Paulo")
        ref_dt = datetime.now(brasil_tz)
        
        result = OpenWeatherDataMapper._generate_alerts_from_forecasts([], ref_dt)
        
        assert result == []

    def test_generate_alerts_no_alerts_in_good_conditions(self):
        """Não deve gerar alertas em condições boas"""
        brasil_tz = ZoneInfo("America/Sao_Paulo")
        now = datetime.now(brasil_tz)
        
        # 8 forecasts com condições ideais (3h cada = 24h)
        forecasts = []
        for i in range(8):
            forecasts.append({
                'dt': int((now + timedelta(hours=3 * i)).timestamp()),
                'main': {
                    'temp': 25.0,
                    'humidity': 60,
                    'feels_like': 26.0
                },
                'weather': [{'main': 'Clear'}],
                'wind': {'speed': 2.0},
                'visibility': 10000,
                'pop': 0.0,
                'rain': {}
            })
        
        result = OpenWeatherDataMapper._generate_alerts_from_forecasts(
            forecasts, 
            now - timedelta(hours=1)
        )
        
        assert len(result) == 0

    def test_generate_alerts_rain_drizzle(self):
        """Deve gerar alerta DRIZZLE para chuva leve"""
        brasil_tz = ZoneInfo("America/Sao_Paulo")
        now = datetime.now(brasil_tz)
        
        forecasts = []
        # Primeiro forecast com garoa (1.5mm em 3h = 0.5mm/h, 100% prob)
        forecasts.append({
            'dt': int((now + timedelta(hours=3)).timestamp()),
            'main': {'temp': 22.0, 'humidity': 85, 'feels_like': 22.0},
            'weather': [{'main': 'Rain'}],
            'wind': {'speed': 3.0},
            'visibility': 8000,
            'pop': 1.0,  # 100%
            'rain': {'3h': 1.5}  # 0.5mm/h
        })
        
        # Adicionar mais alguns forecasts normais
        for i in range(1, 8):
            forecasts.append({
                'dt': int((now + timedelta(hours=3 * (i + 1))).timestamp()),
                'main': {'temp': 25.0, 'humidity': 60, 'feels_like': 25.0},
                'weather': [{'main': 'Clear'}],
                'wind': {'speed': 2.0},
                'visibility': 10000,
                'pop': 0.0,
                'rain': {}
            })
        
        result = OpenWeatherDataMapper._generate_alerts_from_forecasts(
            forecasts,
            now - timedelta(hours=1)
        )
        
        assert len(result) > 0
        drizzle_alerts = [a for a in result if a.code == 'DRIZZLE']
        assert len(drizzle_alerts) > 0

    def test_generate_alerts_strong_wind(self):
        """Deve gerar alerta de vento forte"""
        brasil_tz = ZoneInfo("America/Sao_Paulo")
        now = datetime.now(brasil_tz)
        
        forecasts = []
        # Primeiro forecast com vento forte (15 m/s = 54 km/h)
        forecasts.append({
            'dt': int((now + timedelta(hours=3)).timestamp()),
            'main': {'temp': 25.0, 'humidity': 60, 'feels_like': 25.0},
            'weather': [{'main': 'Clear'}],
            'wind': {'speed': 15.0},  # 54 km/h
            'visibility': 10000,
            'pop': 0.0,
            'rain': {}
        })
        
        # Adicionar mais forecasts normais
        for i in range(1, 8):
            forecasts.append({
                'dt': int((now + timedelta(hours=3 * (i + 1))).timestamp()),
                'main': {'temp': 25.0, 'humidity': 60, 'feels_like': 25.0},
                'weather': [{'main': 'Clear'}],
                'wind': {'speed': 2.0},
                'visibility': 10000,
                'pop': 0.0,
                'rain': {}
            })
        
        result = OpenWeatherDataMapper._generate_alerts_from_forecasts(
            forecasts,
            now - timedelta(hours=1)
        )
        
        wind_alerts = [a for a in result if 'WIND' in a.code]
        assert len(wind_alerts) > 0

    def test_generate_alerts_temp_drop(self):
        """Deve gerar alerta de queda de temperatura ≥8°C"""
        brasil_tz = ZoneInfo("America/Sao_Paulo")
        now = datetime.now(brasil_tz)
        
        forecasts = []
        
        # Dia 1: 35°C (8 forecasts)
        for i in range(8):
            forecasts.append({
                'dt': int((now + timedelta(hours=3 * i)).timestamp()),
                'main': {'temp': 35.0, 'humidity': 50, 'feels_like': 37.0},
                'weather': [{'main': 'Clear'}],
                'wind': {'speed': 2.0},
                'visibility': 10000,
                'pop': 0.0,
                'rain': {}
            })
        
        # Dia 2: 25°C (queda de 10°C - 8 forecasts)
        for i in range(8):
            forecasts.append({
                'dt': int((now + timedelta(days=1, hours=3 * i)).timestamp()),
                'main': {'temp': 25.0, 'humidity': 70, 'feels_like': 26.0},
                'weather': [{'main': 'Clouds'}],
                'wind': {'speed': 3.0},
                'visibility': 10000,
                'pop': 0.0,
                'rain': {}
            })
        
        # Dia 3: 26°C (8 forecasts)
        for i in range(8):
            forecasts.append({
                'dt': int((now + timedelta(days=2, hours=3 * i)).timestamp()),
                'main': {'temp': 26.0, 'humidity': 65, 'feels_like': 27.0},
                'weather': [{'main': 'Clear'}],
                'wind': {'speed': 2.0},
                'visibility': 10000,
                'pop': 0.0,
                'rain': {}
            })
        
        result = OpenWeatherDataMapper._generate_alerts_from_forecasts(
            forecasts,
            now - timedelta(hours=1)
        )
        
        temp_drop_alerts = [a for a in result if a.code == 'TEMP_DROP']
        assert len(temp_drop_alerts) > 0
        
        alert = temp_drop_alerts[0]
        assert 'variation_c' in alert.details
        assert abs(alert.details['variation_c']) >= 8.0
        assert alert.details['variation_c'] < 0  # Negativo = queda

    def test_generate_alerts_temp_rise(self):
        """Deve gerar alerta de aumento de temperatura ≥8°C"""
        brasil_tz = ZoneInfo("America/Sao_Paulo")
        now = datetime.now(brasil_tz)
        
        forecasts = []
        
        # Dia 1: 22°C (8 forecasts)
        for i in range(8):
            forecasts.append({
                'dt': int((now + timedelta(hours=3 * i)).timestamp()),
                'main': {'temp': 22.0, 'humidity': 70, 'feels_like': 23.0},
                'weather': [{'main': 'Clouds'}],
                'wind': {'speed': 3.0},
                'visibility': 10000,
                'pop': 0.0,
                'rain': {}
            })
        
        # Dia 2: 33°C (aumento de 11°C - 8 forecasts)
        for i in range(8):
            forecasts.append({
                'dt': int((now + timedelta(days=1, hours=3 * i)).timestamp()),
                'main': {'temp': 33.0, 'humidity': 50, 'feels_like': 35.0},
                'weather': [{'main': 'Clear'}],
                'wind': {'speed': 2.0},
                'visibility': 10000,
                'pop': 0.0,
                'rain': {}
            })
        
        result = OpenWeatherDataMapper._generate_alerts_from_forecasts(
            forecasts,
            now - timedelta(hours=1)
        )
        
        temp_rise_alerts = [a for a in result if a.code == 'TEMP_RISE']
        assert len(temp_rise_alerts) > 0
        
        alert = temp_rise_alerts[0]
        assert 'variation_c' in alert.details
        assert alert.details['variation_c'] >= 8.0  # Positivo = aumento

    def test_generate_alerts_no_temp_variation_below_threshold(self):
        """Não deve gerar alertas de temperatura com variação <8°C"""
        brasil_tz = ZoneInfo("America/Sao_Paulo")
        now = datetime.now(brasil_tz)
        
        forecasts = []
        temps = [25.0, 26.0, 27.0, 28.0, 29.0]  # Variações pequenas
        
        for day, temp in enumerate(temps):
            for i in range(8):
                forecasts.append({
                    'dt': int((now + timedelta(days=day, hours=3 * i)).timestamp()),
                    'main': {'temp': temp, 'humidity': 60, 'feels_like': temp + 1},
                    'weather': [{'main': 'Clear'}],
                    'wind': {'speed': 2.0},
                    'visibility': 10000,
                    'pop': 0.0,
                    'rain': {}
                })
        
        result = OpenWeatherDataMapper._generate_alerts_from_forecasts(
            forecasts,
            now - timedelta(hours=1)
        )
        
        temp_alerts = [a for a in result if 'TEMP' in a.code and 'DROP' in a.code or 'RISE' in a.code]
        assert len(temp_alerts) == 0

    def test_generate_alerts_multiple_conditions(self):
        """Deve gerar múltiplos alertas para diferentes condições"""
        brasil_tz = ZoneInfo("America/Sao_Paulo")
        now = datetime.now(brasil_tz)
        
        forecasts = []
        
        # Forecast 1: Chuva forte + vento
        forecasts.append({
            'dt': int((now + timedelta(hours=3)).timestamp()),
            'main': {'temp': 35.0, 'humidity': 90, 'feels_like': 38.0},
            'weather': [{'main': 'Rain'}],
            'wind': {'speed': 12.0},  # Vento forte
            'visibility': 5000,  # Baixa visibilidade
            'pop': 1.0,
            'rain': {'3h': 15.0}  # 5mm/h - chuva forte
        })
        
        # Forecasts normais do dia 1
        for i in range(1, 8):
            forecasts.append({
                'dt': int((now + timedelta(hours=3 * (i + 1))).timestamp()),
                'main': {'temp': 34.0, 'humidity': 60, 'feels_like': 35.0},
                'weather': [{'main': 'Clear'}],
                'wind': {'speed': 2.0},
                'visibility': 10000,
                'pop': 0.0,
                'rain': {}
            })
        
        # Dia 2: 22°C (queda de 12°C)
        for i in range(8):
            forecasts.append({
                'dt': int((now + timedelta(days=1, hours=3 * i)).timestamp()),
                'main': {'temp': 22.0, 'humidity': 70, 'feels_like': 23.0},
                'weather': [{'main': 'Clear'}],
                'wind': {'speed': 2.0},
                'visibility': 10000,
                'pop': 0.0,
                'rain': {}
            })
        
        result = OpenWeatherDataMapper._generate_alerts_from_forecasts(
            forecasts,
            now - timedelta(hours=1)
        )
        
        assert len(result) >= 3  # Pelo menos: chuva, vento, temp_drop
        
        codes = {a.code for a in result}
        assert any('RAIN' in code for code in codes)
        assert any('WIND' in code for code in codes)
        assert 'TEMP_DROP' in codes

    def test_generate_alerts_deduplication(self):
        """Deve deduplicar alertas mantendo o mais próximo"""
        brasil_tz = ZoneInfo("America/Sao_Paulo")
        now = datetime.now(brasil_tz)
        
        forecasts = []
        
        # Múltiplos forecasts com chuva forte
        for i in range(4):
            forecasts.append({
                'dt': int((now + timedelta(hours=3 * i)).timestamp()),
                'main': {'temp': 25.0, 'humidity': 90, 'feels_like': 26.0},
                'weather': [{'main': 'Rain'}],
                'wind': {'speed': 3.0},
                'visibility': 8000,
                'pop': 1.0,
                'rain': {'3h': 12.0}  # Chuva forte
            })
        
        # Forecasts normais
        for i in range(4, 8):
            forecasts.append({
                'dt': int((now + timedelta(hours=3 * (i + 1))).timestamp()),
                'main': {'temp': 25.0, 'humidity': 60, 'feels_like': 25.0},
                'weather': [{'main': 'Clear'}],
                'wind': {'speed': 2.0},
                'visibility': 10000,
                'pop': 0.0,
                'rain': {}
            })
        
        result = OpenWeatherDataMapper._generate_alerts_from_forecasts(
            forecasts,
            now - timedelta(hours=1)
        )
        
        # Verificar que há apenas um alerta de chuva (deduplicado)
        rain_alerts = [a for a in result if 'RAIN' in a.code]
        rain_codes = [a.code for a in rain_alerts]
        
        # Não deve haver códigos duplicados
        assert len(rain_codes) == len(set(rain_codes))

    def test_generate_alerts_respects_12h_window_for_immediate_alerts(self):
        """Alertas imediatos devem considerar apenas próximas 12h"""
        brasil_tz = ZoneInfo("America/Sao_Paulo")
        now = datetime.now(brasil_tz)
        
        forecasts = []
        
        # Primeiras 12h: tempo bom
        for i in range(4):  # 12h (4 forecasts de 3h)
            forecasts.append({
                'dt': int((now + timedelta(hours=3 * i)).timestamp()),
                'main': {'temp': 25.0, 'humidity': 60, 'feels_like': 25.0},
                'weather': [{'main': 'Clear'}],
                'wind': {'speed': 2.0},
                'visibility': 10000,
                'pop': 0.0,
                'rain': {}
            })
        
        # Após 12h: chuva forte (não deve gerar alerta imediato)
        for i in range(4, 8):
            forecasts.append({
                'dt': int((now + timedelta(hours=3 * (i + 1))).timestamp()),
                'main': {'temp': 25.0, 'humidity': 90, 'feels_like': 26.0},
                'weather': [{'main': 'Rain'}],
                'wind': {'speed': 3.0},
                'visibility': 8000,
                'pop': 1.0,
                'rain': {'3h': 15.0}
            })
        
        result = OpenWeatherDataMapper._generate_alerts_from_forecasts(
            forecasts,
            now - timedelta(hours=1)
        )
        
        # Não deve ter alertas de chuva imediatos (está após 12h)
        immediate_rain_alerts = [
            a for a in result 
            if 'RAIN' in a.code and (a.timestamp - now).total_seconds() <= 12 * 3600
        ]
        assert len(immediate_rain_alerts) == 0

    def test_generate_alerts_cold_temperature(self):
        """Deve gerar alerta de temperatura baixa"""
        brasil_tz = ZoneInfo("America/Sao_Paulo")
        now = datetime.now(brasil_tz)
        
        forecasts = []
        
        # Forecast com temperatura muito baixa
        forecasts.append({
            'dt': int((now + timedelta(hours=3)).timestamp()),
            'main': {'temp': 8.0, 'humidity': 70, 'feels_like': 6.0},
            'weather': [{'main': 'Clear'}],
            'wind': {'speed': 2.0},
            'visibility': 10000,
            'pop': 0.0,
            'rain': {}
        })
        
        # Forecasts normais
        for i in range(1, 8):
            forecasts.append({
                'dt': int((now + timedelta(hours=3 * (i + 1))).timestamp()),
                'main': {'temp': 25.0, 'humidity': 60, 'feels_like': 25.0},
                'weather': [{'main': 'Clear'}],
                'wind': {'speed': 2.0},
                'visibility': 10000,
                'pop': 0.0,
                'rain': {}
            })
        
        result = OpenWeatherDataMapper._generate_alerts_from_forecasts(
            forecasts,
            now - timedelta(hours=1)
        )
        
        cold_alerts = [a for a in result if a.code == 'COLD']
        assert len(cold_alerts) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
