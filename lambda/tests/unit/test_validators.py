"""
Testes Unitários - Validators
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

import pytest

from shared.utils.validators import RadiusValidator, CityIdValidator
from domain.exceptions import InvalidRadiusException


class TestRadiusValidator:
    """Testes para RadiusValidator"""
    
    def test_validate_minimum_radius(self):
        """Testa validação com raio mínimo (1 km)"""
        result = RadiusValidator.validate(1.0)
        assert result == 1.0
    
    def test_validate_maximum_radius(self):
        """Testa validação com raio máximo (500 km)"""
        result = RadiusValidator.validate(500.0)
        assert result == 500.0
    
    def test_validate_normal_radius(self):
        """Testa validação com raio normal"""
        result = RadiusValidator.validate(50.0)
        assert result == 50.0
    
    def test_validate_radius_zero(self):
        """Testa exceção com raio zero"""
        with pytest.raises(InvalidRadiusException) as exc_info:
            RadiusValidator.validate(0.0)
        
        assert "must be between" in str(exc_info.value)
        assert exc_info.value.details["radius"] == 0.0
        assert exc_info.value.details["min"] == 1.0
        assert exc_info.value.details["max"] == 500.0
    
    def test_validate_radius_negative(self):
        """Testa exceção com raio negativo"""
        with pytest.raises(InvalidRadiusException) as exc_info:
            RadiusValidator.validate(-10.0)
        
        assert "must be between" in str(exc_info.value)
        assert exc_info.value.details["radius"] == -10.0
    
    def test_validate_radius_above_maximum(self):
        """Testa exceção com raio acima do máximo"""
        with pytest.raises(InvalidRadiusException) as exc_info:
            RadiusValidator.validate(1000.0)
        
        assert "must be between" in str(exc_info.value)
        assert exc_info.value.details["radius"] == 1000.0
    
    def test_validate_radius_just_below_minimum(self):
        """Testa exceção com raio logo abaixo do mínimo"""
        with pytest.raises(InvalidRadiusException):
            RadiusValidator.validate(0.9)
    
    def test_validate_radius_just_above_maximum(self):
        """Testa exceção com raio logo acima do máximo"""
        with pytest.raises(InvalidRadiusException):
            RadiusValidator.validate(500.1)
    
    def test_validate_radius_float_precision(self):
        """Testa validação com precisão de ponto flutuante"""
        result = RadiusValidator.validate(50.5)
        assert result == 50.5
        
        result = RadiusValidator.validate(1.001)
        assert result == 1.001
        
        result = RadiusValidator.validate(499.999)
        assert result == 499.999


class TestCityIdValidator:
    """Testes para CityIdValidator"""
    
    def test_validate_valid_city_id(self):
        """Testa validação com ID válido"""
        result = CityIdValidator.validate("3543204")
        assert result == "3543204"
    
    def test_validate_city_id_with_whitespace(self):
        """Testa que trim é feito automaticamente"""
        # O novo validator faz trim antes de validar
        result = CityIdValidator.validate("  3543204  ")
        assert result == "3543204"
    
    def test_validate_city_id_empty_string(self):
        """Testa exceção com string vazia"""
        with pytest.raises(ValueError) as exc_info:
            CityIdValidator.validate("")
        
        assert "cannot be empty" in str(exc_info.value)
    
    def test_validate_city_id_whitespace_only(self):
        """Testa exceção com apenas espaços"""
        with pytest.raises(ValueError) as exc_info:
            CityIdValidator.validate("   ")
        
        assert "cannot be empty" in str(exc_info.value)
    
    def test_validate_city_id_non_numeric(self):
        """Testa exceção com ID não numérico"""
        with pytest.raises(ValueError) as exc_info:
            CityIdValidator.validate("abc123")
        
        assert "Invalid city_id format" in str(exc_info.value)
    
    def test_validate_city_id_with_letters(self):
        """Testa exceção com letras no ID"""
        with pytest.raises(ValueError):
            CityIdValidator.validate("SP3543204")
    
    def test_validate_city_id_with_special_chars(self):
        """Testa exceção com caracteres especiais"""
        with pytest.raises(ValueError):
            CityIdValidator.validate("3543-204")
    
    def test_validate_city_id_short(self):
        """Testa validação com ID curto (ainda válido se for numérico)"""
        result = CityIdValidator.validate("123")
        assert result == "123"
    
    def test_validate_city_id_long(self):
        """Testa validação com ID longo (ainda válido se for numérico)"""
        result = CityIdValidator.validate("123456789")
        assert result == "123456789"
    
    def test_validate_city_id_zero_padded(self):
        """Testa validação com zeros à esquerda"""
        result = CityIdValidator.validate("0003543204")
        assert result == "0003543204"
    
    def test_validate_city_id_with_dots(self):
        """Testa exceção com pontos"""
        with pytest.raises(ValueError):
            CityIdValidator.validate("3.543.204")
    
    def test_validate_typical_ibge_codes(self):
        """Testa validação com códigos IBGE típicos (7 dígitos)"""
        # Códigos IBGE válidos de SP
        valid_codes = [
            "3543204",  # Ribeirão do Sul
            "3548708",  # São Carlos
            "3509502",  # Campinas
            "3550308",  # São Paulo
        ]
        
        for code in valid_codes:
            result = CityIdValidator.validate(code)
            assert result == code
            assert len(result) == 7


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
