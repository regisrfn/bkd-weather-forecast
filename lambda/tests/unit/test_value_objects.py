"""
Testes para Value Objects (Coordinates e Temperature)
"""
import pytest

from domain.value_objects.coordinates import Coordinates
from domain.value_objects.temperature import Temperature, TemperatureScale


class TestCoordinates:
    """Testes para Value Object Coordinates"""
    
    def test_valid_coordinates(self):
        """Testa criação de coordenadas válidas"""
        coords = Coordinates(latitude=-23.5505, longitude=-46.6333)
        assert coords.latitude == -23.5505
        assert coords.longitude == -46.6333
    
    def test_invalid_latitude(self):
        """Testa validação de latitude inválida"""
        with pytest.raises(ValueError, match="Latitude inválida"):
            Coordinates(latitude=100.0, longitude=0.0)
        
        with pytest.raises(ValueError, match="Latitude inválida"):
            Coordinates(latitude=-100.0, longitude=0.0)
    
    def test_invalid_longitude(self):
        """Testa validação de longitude inválida"""
        with pytest.raises(ValueError, match="Longitude inválida"):
            Coordinates(latitude=0.0, longitude=200.0)
        
        with pytest.raises(ValueError, match="Longitude inválida"):
            Coordinates(latitude=0.0, longitude=-200.0)
    
    def test_immutability(self):
        """Testa que Coordinates é imutável"""
        coords = Coordinates(latitude=-23.5505, longitude=-46.6333)
        
        with pytest.raises(Exception):  # FrozenInstanceError
            coords.latitude = 0.0
    
    def test_distance_calculation(self):
        """Testa cálculo de distância entre coordenadas"""
        sao_paulo = Coordinates(-23.5505, -46.6333)
        rio_janeiro = Coordinates(-22.9068, -43.1729)
        
        distance = sao_paulo.distance_to(rio_janeiro)
        
        # Distância aproximada entre SP e RJ é ~357 km
        assert 350 <= distance <= 365
    
    def test_to_tuple(self):
        """Testa conversão para tupla"""
        coords = Coordinates(latitude=-23.5505, longitude=-46.6333)
        
        as_tuple = coords.to_tuple()
        
        assert as_tuple == (-23.5505, -46.6333)
        assert isinstance(as_tuple, tuple)
    
    def test_from_tuple(self):
        """Testa criação a partir de tupla"""
        coords = Coordinates.from_tuple((-23.5505, -46.6333))
        
        assert coords.latitude == -23.5505
        assert coords.longitude == -46.6333
    
    def test_string_representation(self):
        """Testa representação em string"""
        coords = Coordinates(latitude=-23.5505, longitude=-46.6333)
        
        str_repr = str(coords)
        
        assert "23.5505°S" in str_repr
        assert "46.6333°W" in str_repr


class TestTemperature:
    """Testes para Value Object Temperature"""
    
    def test_valid_temperature(self):
        """Testa criação de temperatura válida"""
        temp = Temperature(celsius=25.0)
        assert temp.celsius == 25.0
    
    def test_invalid_temperature_below_absolute_zero(self):
        """Testa validação de temperatura abaixo do zero absoluto"""
        with pytest.raises(ValueError, match="Temperatura impossível"):
            Temperature(celsius=-300.0)
    
    def test_fahrenheit_conversion(self):
        """Testa conversão para Fahrenheit"""
        temp = Temperature(celsius=0.0)
        assert temp.fahrenheit == 32.0
        
        temp2 = Temperature(celsius=100.0)
        assert temp2.fahrenheit == 212.0
        
        temp3 = Temperature(celsius=25.0)
        assert abs(temp3.fahrenheit - 77.0) < 0.1
    
    def test_kelvin_conversion(self):
        """Testa conversão para Kelvin"""
        temp = Temperature(celsius=0.0)
        assert temp.kelvin == 273.15
        
        temp2 = Temperature(celsius=-273.15)
        assert temp2.kelvin == 0.0
    
    def test_is_freezing(self):
        """Testa verificação de congelamento"""
        assert Temperature(celsius=0.0).is_freezing()
        assert Temperature(celsius=-5.0).is_freezing()
        assert not Temperature(celsius=5.0).is_freezing()
    
    def test_is_cold(self):
        """Testa verificação de frio"""
        assert Temperature(celsius=10.0).is_cold()
        assert not Temperature(celsius=15.0).is_cold()
    
    def test_is_hot(self):
        """Testa verificação de calor"""
        assert Temperature(celsius=32.0).is_hot()
        assert not Temperature(celsius=25.0).is_hot()
    
    def test_is_very_cold(self):
        """Testa verificação de muito frio"""
        assert Temperature(celsius=5.0).is_very_cold()
        assert not Temperature(celsius=10.0).is_very_cold()
    
    def test_is_very_hot(self):
        """Testa verificação de muito quente"""
        assert Temperature(celsius=38.0).is_very_hot()
        assert not Temperature(celsius=30.0).is_very_hot()
    
    def test_format_celsius(self):
        """Testa formatação em Celsius"""
        temp = Temperature(celsius=25.5)
        assert temp.format(TemperatureScale.CELSIUS) == "25.5°C"
    
    def test_format_fahrenheit(self):
        """Testa formatação em Fahrenheit"""
        temp = Temperature(celsius=25.0)
        formatted = temp.format(TemperatureScale.FAHRENHEIT)
        assert "°F" in formatted
    
    def test_format_kelvin(self):
        """Testa formatação em Kelvin"""
        temp = Temperature(celsius=25.0)
        formatted = temp.format(TemperatureScale.KELVIN)
        assert "K" in formatted
    
    def test_string_representation(self):
        """Testa representação em string (padrão Celsius)"""
        temp = Temperature(celsius=25.5)
        assert str(temp) == "25.5°C"
    
    def test_float_conversion(self):
        """Testa conversão para float"""
        temp = Temperature(celsius=25.5)
        assert float(temp) == 25.5
    
    def test_from_fahrenheit(self):
        """Testa criação a partir de Fahrenheit"""
        temp = Temperature.from_fahrenheit(32.0)
        assert abs(temp.celsius - 0.0) < 0.01
        
        temp2 = Temperature.from_fahrenheit(212.0)
        assert abs(temp2.celsius - 100.0) < 0.01
    
    def test_from_kelvin(self):
        """Testa criação a partir de Kelvin"""
        temp = Temperature.from_kelvin(273.15)
        assert abs(temp.celsius - 0.0) < 0.01
        
        temp2 = Temperature.from_kelvin(373.15)
        assert abs(temp2.celsius - 100.0) < 0.01
    
    def test_immutability(self):
        """Testa que Temperature é imutável"""
        temp = Temperature(celsius=25.0)
        
        with pytest.raises(Exception):  # FrozenInstanceError
            temp.celsius = 30.0
