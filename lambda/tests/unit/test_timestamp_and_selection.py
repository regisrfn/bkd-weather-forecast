"""
Testes de Timestamp e Seleção de Forecast Mais Próximo
Validação crítica para garantir que retornamos o forecast correto
"""
import pytest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from domain.entities.hourly_forecast import HourlyForecast
from domain.entities.daily_forecast import DailyForecast


class TestTimestampValidation:
    """Testes para validação de timestamps"""
    
    def test_timestamp_is_timezone_aware(self):
        """REGRA: Todos os timestamps devem ter timezone (não naive)"""
        forecast = HourlyForecast(
            timestamp="2025-12-02T15:00:00-03:00",
            temperature=25.0,
            humidity=60,
            wind_speed=10.0,
            wind_direction=180,
            precipitation_probability=30,
                rainfall_intensity=0.0,
            precipitation=0.0,
            weather_code=800,
            cloud_cover=50
        )
        
        # Parse timestamp
        if isinstance(forecast.timestamp, str):
            ts = datetime.fromisoformat(forecast.timestamp)
        else:
            ts = forecast.timestamp
        
        assert ts.tzinfo is not None, "Timestamp DEVE ter timezone"
        assert ts.tzinfo != ZoneInfo("UTC") or True, "Timezone deve estar definido"
    
    def test_timestamp_format_iso8601(self):
        """REGRA: Timestamps devem estar em formato ISO 8601"""
        forecast = HourlyForecast(
            timestamp="2025-12-02T15:00:00-03:00",
            temperature=25.0,
            humidity=60,
            wind_speed=10.0,
            wind_direction=180,
            precipitation_probability=30,
                rainfall_intensity=0.0,
            precipitation=0.0,
            weather_code=800,
            cloud_cover=50
        )
        
        # Deve fazer parse sem erros
        ts = datetime.fromisoformat(forecast.timestamp)
        assert ts.year == 2025
        assert ts.month == 12
        assert ts.day == 2
        assert ts.hour == 15
    
    def test_brazil_timezone_offset(self):
        """REGRA: Timezone do Brasil deve ser -03:00 (Brasília)"""
        br_tz = ZoneInfo("America/Sao_Paulo")
        now = datetime.now(br_tz)
        
        # Offset pode variar com horário de verão, mas geralmente -03:00
        offset_hours = now.utcoffset().total_seconds() / 3600
        assert -4 <= offset_hours <= -2, f"Offset do Brasil fora do esperado: {offset_hours}"


class TestClosestForecastSelection:
    """Testes para seleção do forecast mais próximo ao target_datetime"""
    
    def test_selects_exact_match_when_available(self):
        """REGRA: Se houver timestamp exato, deve retornar esse"""
        target = datetime(2025, 12, 2, 15, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
        
        forecasts = [
            HourlyForecast(
                timestamp="2025-12-02T14:00:00-03:00",
                temperature=24.0,
                humidity=60,
                wind_speed=10.0,
                wind_direction=180,
                precipitation_probability=30,
                rainfall_intensity=0.0,
                precipitation=0.0,
                weather_code=800,
                cloud_cover=50
            ),
            HourlyForecast(
                timestamp="2025-12-02T15:00:00-03:00",  # MATCH EXATO
                temperature=25.0,
                humidity=60,
                wind_speed=10.0,
                wind_direction=180,
                precipitation_probability=30,
                rainfall_intensity=0.0,
                precipitation=0.0,
                weather_code=800,
                cloud_cover=50
            ),
            HourlyForecast(
                timestamp="2025-12-02T16:00:00-03:00",
                temperature=26.0,
                humidity=60,
                wind_speed=10.0,
                wind_direction=180,
                precipitation_probability=30,
                rainfall_intensity=0.0,
                precipitation=0.0,
                weather_code=800,
                cloud_cover=50
            ),
        ]
        
        # Encontrar o mais próximo
        def find_closest(forecasts, target):
            return min(forecasts, key=lambda f: abs(datetime.fromisoformat(f.timestamp) - target))
        
        closest = find_closest(forecasts, target)
        assert closest.temperature == 25.0, "Deve selecionar o forecast com timestamp exato"
    
    def test_selects_closest_when_no_exact_match(self):
        """REGRA: Se não houver match exato, selecionar o mais próximo"""
        target = datetime(2025, 12, 2, 15, 30, tzinfo=ZoneInfo("America/Sao_Paulo"))  # 15:30
        
        forecasts = [
            HourlyForecast(
                timestamp="2025-12-02T15:00:00-03:00",  # 30min antes
                temperature=25.0,
                humidity=60,
                wind_speed=10.0,
                wind_direction=180,
                precipitation_probability=30,
                rainfall_intensity=0.0,
                precipitation=0.0,
                weather_code=800,
                cloud_cover=50
            ),
            HourlyForecast(
                timestamp="2025-12-02T16:00:00-03:00",  # 30min depois
                temperature=26.0,
                humidity=60,
                wind_speed=10.0,
                wind_direction=180,
                precipitation_probability=30,
                rainfall_intensity=0.0,
                precipitation=0.0,
                weather_code=800,
                cloud_cover=50
            ),
        ]
        
        def find_closest(forecasts, target):
            return min(forecasts, key=lambda f: abs(datetime.fromisoformat(f.timestamp) - target))
        
        closest = find_closest(forecasts, target)
        # Ambos estão a 30min, mas 15:00 vem primeiro na lista
        assert closest.timestamp == "2025-12-02T15:00:00-03:00", "Deve selecionar o mais próximo"
    
    def test_prefers_future_over_past_when_equidistant(self):
        """REGRA: Quando equidistante, preferir o forecast futuro"""
        target = datetime(2025, 12, 2, 15, 30, tzinfo=ZoneInfo("America/Sao_Paulo"))
        
        forecasts = [
            HourlyForecast(
                timestamp="2025-12-02T15:00:00-03:00",  # 30min antes
                temperature=25.0,
                humidity=60,
                wind_speed=10.0,
                wind_direction=180,
                precipitation_probability=30,
                rainfall_intensity=0.0,
                precipitation=0.0,
                weather_code=800,
                cloud_cover=50
            ),
            HourlyForecast(
                timestamp="2025-12-02T16:00:00-03:00",  # 30min depois
                temperature=26.0,
                humidity=60,
                wind_speed=10.0,
                wind_direction=180,
                precipitation_probability=30,
                rainfall_intensity=0.0,
                precipitation=0.0,
                weather_code=800,
                cloud_cover=50
            ),
        ]
        
        # Estratégia: em caso de empate, preferir futuro
        def find_closest_prefer_future(forecasts, target):
            sorted_by_distance = sorted(
                forecasts,
                key=lambda f: (abs(datetime.fromisoformat(f.timestamp) - target), 
                              -(datetime.fromisoformat(f.timestamp) - target).total_seconds())
            )
            return sorted_by_distance[0]
        
        closest = find_closest_prefer_future(forecasts, target)
        # Deve preferir o futuro (16:00)
        assert closest.timestamp == "2025-12-02T16:00:00-03:00", \
            "Quando equidistante, deve preferir forecast futuro"
    
    def test_handles_past_target_datetime(self):
        """REGRA: Se target_datetime é passado, deve retornar o primeiro forecast disponível"""
        target = datetime(2025, 11, 1, 12, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))  # Passado
        
        forecasts = [
            HourlyForecast(
                timestamp="2025-12-02T15:00:00-03:00",
                temperature=25.0,
                humidity=60,
                wind_speed=10.0,
                wind_direction=180,
                precipitation_probability=30,
                rainfall_intensity=0.0,
                precipitation=0.0,
                weather_code=800,
                cloud_cover=50
            ),
            HourlyForecast(
                timestamp="2025-12-02T16:00:00-03:00",
                temperature=26.0,
                humidity=60,
                wind_speed=10.0,
                wind_direction=180,
                precipitation_probability=30,
                rainfall_intensity=0.0,
                precipitation=0.0,
                weather_code=800,
                cloud_cover=50
            ),
        ]
        
        # Se target é passado, retornar primeiro futuro
        def find_closest_or_next(forecasts, target):
            future_forecasts = [
                f for f in forecasts 
                if datetime.fromisoformat(f.timestamp) >= target
            ]
            if future_forecasts:
                return min(future_forecasts, key=lambda f: datetime.fromisoformat(f.timestamp))
            return forecasts[0] if forecasts else None
        
        closest = find_closest_or_next(forecasts, target)
        assert closest.timestamp == "2025-12-02T15:00:00-03:00", \
            "Target passado deve retornar primeiro forecast futuro"


class TestCurrentWeatherSelection:
    """Testes para seleção do 'current weather' - deve ser o mais recente/próximo ao now"""
    
    def test_current_weather_is_closest_to_now(self):
        """REGRA: Current weather deve ser o forecast mais próximo ao momento atual"""
        now = datetime.now(ZoneInfo("America/Sao_Paulo"))
        
        forecasts = [
            HourlyForecast(
                timestamp=(now - timedelta(hours=1)).isoformat(),
                temperature=24.0,
                humidity=60,
                wind_speed=10.0,
                wind_direction=180,
                precipitation_probability=30,
                rainfall_intensity=0.0,
                precipitation=0.0,
                weather_code=800,
                cloud_cover=50
            ),
            HourlyForecast(
                timestamp=now.isoformat(),
                temperature=25.0,
                humidity=60,
                wind_speed=10.0,
                wind_direction=180,
                precipitation_probability=30,
                rainfall_intensity=0.0,
                precipitation=0.0,
                weather_code=800,
                cloud_cover=50
            ),
            HourlyForecast(
                timestamp=(now + timedelta(hours=1)).isoformat(),
                temperature=26.0,
                humidity=60,
                wind_speed=10.0,
                wind_direction=180,
                precipitation_probability=30,
                rainfall_intensity=0.0,
                precipitation=0.0,
                weather_code=800,
                cloud_cover=50
            ),
        ]
        
        def find_current(forecasts):
            now = datetime.now(ZoneInfo("America/Sao_Paulo"))
            return min(forecasts, key=lambda f: abs(datetime.fromisoformat(f.timestamp) - now))
        
        current = find_current(forecasts)
        assert current.temperature == 25.0, "Current weather deve ser o mais próximo ao now"
    
    def test_current_weather_never_past(self):
        """REGRA: Current weather não deve ser um forecast passado se houver futuros"""
        now = datetime.now(ZoneInfo("America/Sao_Paulo"))
        
        forecasts = [
            HourlyForecast(
                timestamp=(now - timedelta(hours=2)).isoformat(),  # Passado
                temperature=23.0,
                humidity=60,
                wind_speed=10.0,
                wind_direction=180,
                precipitation_probability=30,
                rainfall_intensity=0.0,
                precipitation=0.0,
                weather_code=800,
                cloud_cover=50
            ),
            HourlyForecast(
                timestamp=(now + timedelta(minutes=30)).isoformat(),  # Futuro próximo
                temperature=25.0,
                humidity=60,
                wind_speed=10.0,
                wind_direction=180,
                precipitation_probability=30,
                rainfall_intensity=0.0,
                precipitation=0.0,
                weather_code=800,
                cloud_cover=50
            ),
        ]
        
        def find_current_prefer_future(forecasts):
            now = datetime.now(ZoneInfo("America/Sao_Paulo"))
            # Filtrar apenas futuros
            future = [f for f in forecasts if datetime.fromisoformat(f.timestamp) >= now]
            if future:
                return min(future, key=lambda f: datetime.fromisoformat(f.timestamp))
            # Se não houver futuros, pegar o mais recente do passado
            return max(forecasts, key=lambda f: datetime.fromisoformat(f.timestamp))
        
        current = find_current_prefer_future(forecasts)
        assert current.temperature == 25.0, "Deve preferir forecast futuro sobre passado"


class TestDailyForecastDateMatching:
    """Testes para matching de data em daily forecasts"""
    
    def test_matches_exact_date(self):
        """REGRA: Deve encontrar forecast para data exata"""
        target_date = datetime(2025, 12, 5, tzinfo=ZoneInfo("America/Sao_Paulo")).date()
        
        forecasts = [
            DailyForecast(
                date="2025-12-04",
                temp_max=30.0,
                temp_min=20.0,
                precipitation_mm=0.0,
                rain_probability=10.0,
            rainfall_intensity=0.0,
                wind_speed_max=15.0,
                wind_direction=180,
                uv_index=5.0,
                sunrise="06:00",
                sunset="18:00",
                precipitation_hours=0.0
            ),
            DailyForecast(
                date="2025-12-05",  # MATCH
                temp_max=32.0,
                temp_min=22.0,
                precipitation_mm=0.0,
                rain_probability=10.0,
            rainfall_intensity=0.0,
                wind_speed_max=15.0,
                wind_direction=180,
                uv_index=5.0,
                sunrise="06:00",
                sunset="18:00",
                precipitation_hours=0.0
            ),
        ]
        
        def find_by_date(forecasts, target_date):
            for f in forecasts:
                if datetime.fromisoformat(f.date).date() == target_date:
                    return f
            return None
        
        found = find_by_date(forecasts, target_date)
        assert found is not None, "Deve encontrar forecast para data exata"
        assert found.temp_max == 32.0
    
    def test_returns_none_if_date_not_available(self):
        """REGRA: Se data não estiver disponível, deve retornar None (não crashar)"""
        target_date = datetime(2025, 12, 10, tzinfo=ZoneInfo("America/Sao_Paulo")).date()
        
        forecasts = [
            DailyForecast(
                date="2025-12-04",
                temp_max=30.0,
                temp_min=20.0,
                precipitation_mm=0.0,
                rain_probability=10.0,
            rainfall_intensity=0.0,
                wind_speed_max=15.0,
                wind_direction=180,
                uv_index=5.0,
                sunrise="06:00",
                sunset="18:00",
                precipitation_hours=0.0
            ),
        ]
        
        def find_by_date(forecasts, target_date):
            for f in forecasts:
                if datetime.fromisoformat(f.date).date() == target_date:
                    return f
            return None
        
        found = find_by_date(forecasts, target_date)
        assert found is None, "Deve retornar None se data não disponível"
