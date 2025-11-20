"""
Testes Unitários - Use Case GetCityWeather
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lambda'))

import pytest
from unittest.mock import Mock
from datetime import datetime
from application.use_cases.get_city_weather import GetCityWeatherUseCase
from domain.entities.city import City
from domain.entities.weather import Weather


class MockCityRepository:
    """Mock do repositório de cidades"""
    
    def get_by_id(self, city_id: str):
        if city_id == "3543204":
            return City(
                id="3543204",
                name="Ribeirão Preto",
                state="SP",
                region="Sudeste",
                latitude=-21.1704,
                longitude=-47.8103
            )
        elif city_id == "9999999":
            return City(
                id="9999999",
                name="Sem Coordenadas",
                state="SP",
                region="Sudeste",
                latitude=None,
                longitude=None
            )
        return None


class MockWeatherRepository:
    """Mock do repositório de clima"""
    
    def get_current_weather(self, latitude, longitude, city_name, target_datetime=None):
        return Weather(
            city_id="",
            city_name=city_name,
            timestamp=datetime(2025, 11, 20, 15, 0),
            temperature=28.5,
            humidity=65,
            wind_speed=15.2,
            rain_probability=45.0,
            rain_1h=2.5
        )


def test_get_city_weather_success():
    """Testa busca de clima com sucesso"""
    city_repo = MockCityRepository()
    weather_repo = MockWeatherRepository()
    use_case = GetCityWeatherUseCase(city_repo, weather_repo)
    
    weather = use_case.execute("3543204")
    
    assert weather.city_name == "Ribeirão Preto"
    assert weather.temperature == 28.5
    assert weather.humidity == 65
    assert weather.wind_speed == 15.2
    assert weather.rain_probability == 45.0


def test_get_city_weather_city_not_found():
    """Testa erro quando cidade não encontrada"""
    city_repo = MockCityRepository()
    weather_repo = MockWeatherRepository()
    use_case = GetCityWeatherUseCase(city_repo, weather_repo)
    
    with pytest.raises(ValueError, match="não encontrada"):
        use_case.execute("8888888")


def test_get_city_weather_no_coordinates():
    """Testa erro quando cidade não possui coordenadas"""
    city_repo = MockCityRepository()
    weather_repo = MockWeatherRepository()
    use_case = GetCityWeatherUseCase(city_repo, weather_repo)
    
    with pytest.raises(ValueError, match="não possui coordenadas"):
        use_case.execute("9999999")


def test_get_city_weather_with_target_datetime():
    """Testa busca com data/hora específica"""
    city_repo = MockCityRepository()
    weather_repo = MockWeatherRepository()
    use_case = GetCityWeatherUseCase(city_repo, weather_repo)
    
    target_dt = datetime(2025, 11, 21, 18, 0)
    weather = use_case.execute("3543204", target_dt)
    
    assert weather is not None
    assert weather.city_name == "Ribeirão Preto"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
